-- Illustrated (direction D) styling filter for the CTF writeup.
-- Transforms: challenge headers -> header card + hero diagram;
-- the four part lead-ins -> icon part-headers; code blocks -> cmd/output/flag boxes;
-- the prevent bullet list -> a tinted prevent card.

local function raw(s) return pandoc.RawBlock('latex', s) end

local catcolor = {
  web = 'catweb', crypto = 'catcrypto', forensics = 'catforensics',
  misc = 'catmisc', pwn = 'catpwn',
}
local function colour_for(cat)
  if cat:match('^ai%-') then return 'catai' end
  return catcolor[cat] or 'muted'
end

local function diff_from_points(p)
  p = tonumber(p) or 0
  if p <= 20 then return 1 elseif p <= 50 then return 2
  elseif p <= 90 then return 3 elseif p <= 150 then return 4 else return 5 end
end

-- escape for LaTeX text (names, categories are plain ASCII here)
local function esc(s)
  return (s:gsub('([#%$%%&_{}])', '\\%1'))
end

-- is this header a challenge? pattern "name — category — NN points"
local function parse_challenge(h)
  local txt = pandoc.utils.stringify(h.content)
  -- em dash separators
  local name, cat, pts = txt:match('^(.-)%s+—%s+(.-)%s+—%s+(%d+)%s+points%s*$')
  if not name then return nil end
  return name, cat, pts
end

local LABELS = {
  ['What you learn'] = 'Learn',
  ['How to solve it'] = 'Solve',
  ['Why it works'] = 'Why',
  ['How to prevent it'] = 'Prevent',
}

-- detect a part lead paragraph: first inline Strong matching a label (trailing '.')
local function part_label(blk)
  if blk.t ~= 'Para' then return nil end
  local first = blk.content[1]
  if not first or first.t ~= 'Strong' then return nil end
  local s = pandoc.utils.stringify(first):gsub('%.%s*$', '')
  return LABELS[s]
end

-- a real flag: only flag-legal characters (so a grep pattern like flag{[^}]*} never matches)
local FLAGPAT = 'flag%{[%w_%.@&%$%?!%-]*%}'
local function find_flag(code)
  return code:match('(' .. FLAGPAT .. ')')
end
-- does a code block look like a command the reader types (vs. program output)?
local CMDWORD = {}
for w in ([[curl python3 python base64 base32 nc ncat grep find ls cat sed tr awk make
  pdfcrack pdftotext pdfinfo zbarimg convert mkdir unzip file git sqlite3 wget echo printf
  objdump nm for sudo pip3 gem strings tail head xxd chmod export apt]]):gmatch('%S+') do
  CMDWORD[w] = true
end
local function is_command(code)
  for ln in (code .. '\n'):gmatch('(.-)\n') do
    ln = ln:gsub('^%s+', '')
    if ln ~= '' then
      if ln:match('^[%u][%u%d_]*=') then return true end        -- VAR=...
      if ln:match('^%./') or ln:match('^%$ ') or ln:match('^# ') then return true end
      local w = ln:match('^([%w_%.]+)')
      if w and CMDWORD[w] then return true end
      return false  -- first real line is not a command => output
    end
  end
  return false
end

-- drop a trailing line that is exactly the flag (the flag bar shows it instead)
local function strip_trailing_flag(code, flag)
  local lines = {}
  for ln in (code .. '\n'):gmatch('(.-)\n') do lines[#lines+1] = ln end
  while #lines > 0 and lines[#lines]:match('^%s*$') do table.remove(lines) end
  if #lines > 0 and lines[#lines]:gsub('%s','') == flag then table.remove(lines) end
  return table.concat(lines, '\n')
end

function Pandoc(doc)
  local out = {}
  local blocks = doc.blocks
  local i = 1
  while i <= #blocks do
    local b = blocks[i]

    if b.t == 'Header' and b.level == 2 then
      local name, cat, pts = parse_challenge(b)
      if name then
        local col = colour_for(cat)
        local diff = b.attributes['diff'] or diff_from_points(pts)
        local hero = b.attributes['hero'] or name:gsub('%s+$',''):lower()
        -- bookmark + running head target
        local header = string.format([[
\clearpage
\phantomsection\addcontentsline{toc}{subsection}{%s — %s — %s points}\markboth{%s}{%s}
\par\vspace{2pt}
{\dispfont\bfseries\fontsize{28}{30}\selectfont %s}\hfill\raisebox{2pt}{\catpill{%s}{%s}}\\[1pt]
{\footnotesize\color{muted}\textbf{%s} points \quad\textcolor{line}{\textbar}\quad difficulty \diffdots{%s}}
\par\vspace{3pt}
\herocard{%s}
]], esc(name), esc(cat), pts, esc(name), esc(cat),
    esc(name), col, esc(cat), pts, tostring(diff), hero)
        table.insert(out, raw(header))
        i = i + 1
        goto continue
      end
    end

    -- part lead-ins
    local lab = part_label(b)
    if lab then
      local cmd = { Learn='\\LearnHead', Solve='\\SolveHead', Why='\\WhyHead', Prevent='\\PreventHead' }
      table.insert(out, raw(cmd[lab]))
      -- remaining inlines after the Strong (for Learn/Why the text follows inline)
      local rest = {}
      for j = 2, #b.content do rest[#rest+1] = b.content[j] end
      -- drop a leading space
      if rest[1] and rest[1].t == 'Space' then table.remove(rest, 1) end
      if #rest > 0 then table.insert(out, pandoc.Para(rest)) end
      if lab == 'Prevent' then
        -- wrap the following bullet list in a prevent card
        local nxt = blocks[i+1]
        if nxt and nxt.t == 'BulletList' then
          table.insert(out, raw('\\begin{preventcard}'))
          table.insert(out, nxt)
          table.insert(out, raw('\\end{preventcard}'))
          i = i + 2
          goto continue
        end
      end
      i = i + 1
      goto continue
    end

    -- code blocks
    if b.t == 'CodeBlock' then
      local code = b.text
      local flag = find_flag(code)
      if flag then
        local rest = strip_trailing_flag(code:gsub('%s+$',''), flag)
        if rest:match('%S') then
          table.insert(out, raw('\\begin{outbox}\n' .. rest .. '\n\\end{outbox}'))
        end
        table.insert(out, raw('\\flagbar{' .. esc(flag) .. '}'))
      elseif b.classes:includes('output') or not is_command(code) then
        table.insert(out, raw('\\begin{outbox}\n' .. code .. '\n\\end{outbox}'))
      else
        table.insert(out, raw('\\begin{cmdbox}\n' .. code .. '\n\\end{cmdbox}'))
      end
      i = i + 1
      goto continue
    end

    table.insert(out, b)
    i = i + 1
    ::continue::
  end

  doc.blocks = out
  return doc
end
