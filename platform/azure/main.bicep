// Azure resources for hosting the CTF on one VM. Deployed by ./azure.sh (docs/azure.md),
// which also sets the resource group's tags, DNS and the VM's contents.
//
// Names follow the <type>-<env>-<workload> order (rsg-tst-ctf, vnet-prd-ctf); the type
// prefixes are the Microsoft CAF abbreviations.

@description('Environment code.')
@allowed([
  'tst'
  'prd'
])
param env string

@description('Workload part of every resource name.')
param workload string = 'ctf'

param location string = resourceGroup().location

@description('An x86-64 size, so the pwn binaries run natively.')
param vmSize string = 'Standard_D4s_v5'

param adminUsername string = 'ctfadmin'

@description('OpenSSH public key for adminUsername. Azure fixes it when the VM is created.')
param sshPublicKey string

@description('Addresses (CIDR) that may use SSH, and that reach the challenges while they are closed.')
@minLength(1)
param adminSourcePrefixes array

@description('Host ports and port ranges the challenges publish (compose.yml), e.g. 4441-4446.')
@minLength(1)
param challengePorts array

@description('true: the challenges are reachable from the internet (the event). false: only from adminSourcePrefixes and playerSourcePrefixes.')
param challengesOpen bool = false

@description('Addresses (CIDR) that reach the challenges at all times, but not SSH, e.g. the office and its VPN.')
param playerSourcePrefixes array = []

@description('Daily shutdown (deallocation) time, HHmm in Europe/Oslo time.')
param autoShutdownTime string = '2300'

@description('Nightly shutdown while the challenges are closed. It is always off while they are open, so the VM can\'t stop mid-event.')
param autoShutdownEnabled bool = true

@description('Morning start, HHmm in Europe/Oslo time, Monday to Friday.')
param autoStartTime string = '0730'

@description('Start the VM every weekday morning, e.g. after the nightly shutdown. Off unless asked for.')
param autoStartEnabled bool = false

@description('Receives the shutdown warning 30 minutes ahead, with a link to postpone it. Empty: no email.')
param notificationEmail string = ''

@description('Tags for every resource. expires-on is set on the resource group only.')
param tags object = {}

var name = '${env}-${workload}'
// srv-, not vm-: the tenant's naming policy denies any other virtual machine name.
var vmName = 'srv-${name}'

// The challenge rule's source: the internet during the event, the admins otherwise.
var challengeSource = challengesOpen
  ? { sourceAddressPrefix: 'Internet' }
  : { sourceAddressPrefixes: adminSourcePrefixes }

// Players' addresses reach the challenges whether they are open or closed, and
// never SSH. A rule of its own, so azure.sh can read them back from Azure.
var playerRules = empty(playerSourcePrefixes)
  ? []
  : [
      {
        name: 'allow-challenges-players'
        properties: {
          priority: 140
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefixes: playerSourcePrefixes
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRanges: challengePorts
        }
      }
    ]

resource nsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-${name}'
  location: location
  tags: tags
  properties: {
    securityRules: concat([
      {
        name: 'allow-ssh-admin'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefixes: adminSourcePrefixes
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '22'
        }
      }
      {
        // Always open: Let's Encrypt validates from addresses nobody can allow-list.
        name: 'allow-ctfd-web'
        properties: {
          priority: 110
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRanges: [
            '80'
            '443'
          ]
        }
      }
      {
        name: 'allow-ctfd-http3'
        properties: {
          priority: 120
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Udp'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '443'
        }
      }
      {
        name: 'allow-challenges'
        properties: union(
          {
            priority: 130
            direction: 'Inbound'
            access: 'Allow'
            protocol: 'Tcp'
            sourcePortRange: '*'
            destinationAddressPrefix: '*'
            destinationPortRanges: challengePorts
          },
          challengeSource
        )
      }
    ], playerRules)
  }
}

// A network of its own, peered with nothing: a player's shell stays on this VM.
resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: 'vnet-${name}'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.231.0.0/24'
      ]
    }
    subnets: [
      {
        name: 'snet-${name}'
        properties: {
          addressPrefix: '10.231.0.0/27'
          networkSecurityGroup: {
            id: nsg.id
          }
        }
      }
    ]
  }
}

resource pip 'Microsoft.Network/publicIPAddresses@2024-05-01' = {
  name: 'pip-${name}'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
  }
}

resource nic 'Microsoft.Network/networkInterfaces@2024-05-01' = {
  name: 'nic-${name}'
  location: location
  tags: tags
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          subnet: {
            id: vnet.properties.subnets[0].id
          }
          publicIPAddress: {
            id: pip.id
          }
        }
      }
    ]
  }
}

// No managed identity: challenge containers hand players a shell, so the VM holds no
// credentials for anything else in Azure.
resource vm 'Microsoft.Compute/virtualMachines@2024-07-01' = {
  name: vmName
  location: location
  tags: tags
  properties: {
    hardwareProfile: {
      vmSize: vmSize
    }
    osProfile: {
      computerName: vmName
      adminUsername: adminUsername
      linuxConfiguration: {
        disablePasswordAuthentication: true
        ssh: {
          publicKeys: [
            {
              path: '/home/${adminUsername}/.ssh/authorized_keys'
              keyData: sshPublicKey
            }
          ]
        }
      }
    }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: 'ubuntu-24_04-lts'
        sku: 'server'
        version: 'latest'
      }
      osDisk: {
        name: 'osdisk-${name}'
        createOption: 'FromImage'
        diskSizeGB: 64
        managedDisk: {
          storageAccountType: 'StandardSSD_LRS'
        }
        deleteOption: 'Delete'
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: nic.id
          properties: {
            deleteOption: 'Delete'
          }
        }
      ]
    }
    securityProfile: {
      securityType: 'TrustedLaunch'
      uefiSettings: {
        secureBootEnabled: true
        vTpmEnabled: true
      }
    }
    // Serial console, for when SSH is locked out.
    diagnosticsProfile: {
      bootDiagnostics: {
        enabled: true
      }
    }
  }
}

// The name is fixed by Azure: the portal's Auto-shutdown blade looks for exactly this.
// The auto-shutdown tag keeps the setting while open overrides the status, so close
// restores what was chosen.
resource shutdown 'Microsoft.DevTestLab/schedules@2018-09-15' = {
  name: 'shutdown-computevm-${vmName}'
  location: location
  tags: union(tags, {
    'auto-shutdown': autoShutdownEnabled ? 'on' : 'off'
  })
  properties: {
    status: autoShutdownEnabled && !challengesOpen ? 'Enabled' : 'Disabled'
    taskType: 'ComputeVmShutdownTask'
    dailyRecurrence: {
      time: autoShutdownTime
    }
    timeZoneId: 'W. Europe Standard Time'
    targetResourceId: vm.id
    notificationSettings: empty(notificationEmail)
      ? {
          status: 'Disabled'
        }
      : {
          status: 'Enabled'
          emailRecipient: notificationEmail
          notificationLocale: 'en'
          timeInMinutes: 30
        }
  }
}

// The nightly expiry job and the morning start each run as their own system-assigned
// identity: the expiry job needs Contributor on the group, the morning start Virtual
// Machine Contributor on the VM (only while it is enabled). azure.sh grants them after
// the deployment, which takes Owner or User Access Administrator. The expiry job keeps the
// identity it has always had, so a group an Owner has armed stays armed: moving it to
// another identity would drop that role assignment, and the fail-safe with it.
var armAuth = {
  type: 'ManagedServiceIdentity'
  audience: environment().resourceManager
}

// Every night at 03:00 Oslo time: read the resource group's expires-on tag and delete
// the group once that day has passed. The tag is the only setting, so extending the
// deployment is a tag change. A missing tag never expires, and neither does one that
// isn't exactly YYYY-MM-DD (an emptied tag, 01.12.2026, ...): those fail safe instead
// of comparing as text.
var rgUri = '${environment().resourceManager}subscriptions/${subscription().subscriptionId}/resourceGroups/${resourceGroup().name}?api-version=2021-04-01'
var expiresOn = 'coalesce(body(\'Read_resource_group\')?[\'tags\']?[\'expires-on\'], \'9999-12-31\')'

resource expiry 'Microsoft.Logic/workflows@2019-05-01' = {
  name: 'logic-${name}-expiry'
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    state: 'Enabled'
    definition: {
      '$schema': 'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#'
      contentVersion: '1.0.0.0'
      triggers: {
        Nightly: {
          type: 'Recurrence'
          recurrence: {
            frequency: 'Day'
            interval: 1
            startTime: '2026-01-01T03:00:00'
            timeZone: 'W. Europe Standard Time'
          }
        }
      }
      actions: {
        Read_resource_group: {
          type: 'Http'
          inputs: {
            method: 'GET'
            uri: rgUri
            authentication: armAuth
          }
        }
        If_expired: {
          type: 'If'
          runAfter: {
            Read_resource_group: [
              'Succeeded'
            ]
          }
          expression: {
            and: [
              {
                // Only an exact YYYY-MM-DD survives the round trip; formatDateTime fails on
                // anything it can't parse, which fails this run without deleting.
                equals: [
                  '@formatDateTime(concat(${expiresOn}, \'T00:00:00Z\'), \'yyyy-MM-dd\')'
                  '@${expiresOn}'
                ]
              }
              {
                less: [
                  '@${expiresOn}'
                  '@utcNow(\'yyyy-MM-dd\')'
                ]
              }
            ]
          }
          actions: {
            // Done once Azure accepts the deletion: polling it would outlive this workflow,
            // which is deleted along with the group.
            Delete_resource_group: {
              type: 'Http'
              inputs: {
                method: 'DELETE'
                uri: rgUri
                authentication: armAuth
              }
              operationOptions: 'DisableAsyncPattern'
            }
          }
          else: {
            actions: {}
          }
        }
      }
    }
  }
}

// Monday to Friday at autoStartTime: start the VM, typically after the nightly
// shutdown. Starting a running VM changes nothing. The auto-start tag holds the
// setting (HHmm or off) for azure.sh to read back.
resource start 'Microsoft.Logic/workflows@2019-05-01' = {
  name: 'logic-${name}-start'
  location: location
  tags: union(tags, {
    'auto-start': autoStartEnabled ? autoStartTime : 'off'
  })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    state: autoStartEnabled ? 'Enabled' : 'Disabled'
    definition: {
      '$schema': 'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#'
      contentVersion: '1.0.0.0'
      triggers: {
        Weekday_morning: {
          type: 'Recurrence'
          recurrence: {
            frequency: 'Week'
            interval: 1
            startTime: '2026-01-01T00:00:00'
            timeZone: 'W. Europe Standard Time'
            schedule: {
              weekDays: [
                'Monday'
                'Tuesday'
                'Wednesday'
                'Thursday'
                'Friday'
              ]
              hours: [
                int(substring(autoStartTime, 0, 2))
              ]
              minutes: [
                int(substring(autoStartTime, 2, 2))
              ]
            }
          }
        }
      }
      actions: {
        // Done once Azure accepts the start; the VM is up about a minute later.
        Start_VM: {
          type: 'Http'
          inputs: {
            method: 'POST'
            uri: '${environment().resourceManager}${substring(vm.id, 1)}/start?api-version=2024-03-01'
            authentication: armAuth
          }
          operationOptions: 'DisableAsyncPattern'
        }
      }
    }
  }
}

output publicIp string = pip.properties.ipAddress
output publicIpId string = pip.id
output vmName string = vm.name
output expiryPrincipalId string = expiry.identity.principalId
output startPrincipalId string = start.identity.principalId
