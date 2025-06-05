local timestamp_pattern = "^%d%d:%d%d:%d%d,%d%d%d%s+-->%s+%d%d:%d%d:%d%d,%d%d%d$"
local single_number_pattern = "^%d+$"


local function JoinLines()
  -- Go to start of paragraph
  vim.cmd('normal! {')
  local start_lnum = vim.fn.line('.')

  -- Go to end of paragraph
  vim.cmd('normal! }')
  local end_lnum = vim.fn.line('.')

  -- Collect lines in the paragraph
  local lines = {}
  for lnum = start_lnum, end_lnum do
    table.insert(lines, vim.fn.getline(lnum))
  end

  if #lines <= 2 then
    -- Nothing to join, just return
    return
  end

  -- First and second lines unchanged
  local new_lines = { lines[1], lines[2] }

  -- Join third and onward lines after stripping whitespace
  local to_join = {}
  for i = 3, #lines do
    local stripped = lines[i]:gsub('^%s+', ''):gsub('%s+$', '')
    table.insert(to_join, stripped)
  end

  if #to_join > 0 then
    table.insert(new_lines, table.concat(to_join, ' '))
  end

  -- Replace paragraph in buffer
  vim.fn.setline(start_lnum, new_lines)
  -- Delete any extra lines if the new paragraph is shorter
  if #new_lines < #lines then
    vim.fn.deletebufline('%', start_lnum + #new_lines, start_lnum + #lines - 1)
  end
end


local function ClearBlankLines()
  -- Jump to start of paragraph
  vim.cmd('normal! {')
  local start_line = vim.fn.line('.')
  -- Find end of paragraph
  vim.cmd('normal! }')
  local end_line = vim.fn.line('.')
  -- Check that there are at least three lines in paragraph
  -- Should be number, timestamp, and subtitle content
  -- Otherwise, skip
  -- TODO: Impelement

  -- Delete blank lines in the paragraph
  lnum = start_line
  while vim.fn.getline(lnum):match("^%s*$") and lnum <= vim.fn.line('$') do
    vim.fn.deletebufline('%', lnum)
    -- Do not increment lnum, as lines shift up
    end_line = end_line - 1
  end
end


local function DelFirstParagraph()
  -- Jump to start of paragraph
  vim.cmd('normal! {')
  local start_line = vim.fn.line('.')
  -- Find end of paragraph
  vim.cmd('normal! }')
  local end_line = vim.fn.line('.')
  if start_line > end_line then start_line, end_line = end_line, start_line end

  for lnum = start_line, end_line do
    local line = vim.fn.getline(lnum)
    -- Only process lines with the timestamp pattern
    if line:match(timestamp_pattern) then
      -- Remove the timestamp after -->
      local before, arrow, after = line:match("^(.-)(%-%-%>%s*)(%d%d:%d%d:%d%d,%d%d%d)$")
      if before and arrow then
        -- Keep everything before --> and the arrow itself, remove the timestamp after
        vim.fn.setline(lnum, before .. arrow)
      end
    end
    -- Do not delete lines with only a single number
  end
  -- Jump to next paragraph
  vim.cmd('normal! }')
end


local function DelParagraph()
  -- Jump to start of paragraph
  vim.cmd('normal! {')
  local start_line = vim.fn.line('.')
  -- Find end of paragraph
  vim.cmd('normal! }')
  local end_line = vim.fn.line('.')
  if start_line > end_line then start_line, end_line = end_line, start_line end

  -- Delete matching lines in the paragraph
  local lines_to_delete = {}
  for lnum = start_line, end_line do
    local line = vim.fn.getline(lnum)
    if line:match(timestamp_pattern) or line:match(single_number_pattern) then
      table.insert(lines_to_delete, lnum)
    end
  end
  for i = #lines_to_delete, 1, -1 do
    vim.fn.deletebufline('%', lines_to_delete[i])
  end

  ClearBlankLines()

  -- Jump to next paragraph
  vim.cmd('normal! }')
end


local function DelLastParagraph()
  -- Jump to start of paragraph
  vim.cmd('normal! {')
  local start_line = vim.fn.line('.')
  -- Find end of paragraph
  vim.cmd('normal! }')
  local end_line = vim.fn.line('.')
  if start_line > end_line then start_line, end_line = end_line, start_line end

  -- Variable to store the timestamp
  local last_timestamp = nil

  -- Mark matching lines for deletion and update last_timestamp
  local lines_to_delete = {}
  for lnum = start_line, end_line do
    local line = vim.fn.getline(lnum)
    if line:match(timestamp_pattern) then
      -- Extract the second timestamp after arrow (`-->`)
      local after = line:match("-->%s*(%d%d:%d%d:%d%d,%d%d%d)")
      if after then
        last_timestamp = after
      end
      table.insert(lines_to_delete, lnum)
    elseif line:match(single_number_pattern) then
      table.insert(lines_to_delete, lnum)
    end
  end
  --Execute line deletion
  for i = #lines_to_delete, 1, -1 do
    vim.fn.deletebufline('%', lines_to_delete[i])
  end

  ClearBlankLines()

  -- Write the second timestamp to merge with the timestamp of first subtitle
  vim.cmd('normal! {')
  local lnum = vim.fn.line('.')
  local last = vim.fn.line('$')
  while lnum <= last do
    local line = vim.fn.getline(lnum)
    if line:match("^%d%d:%d%d:%d%d,%d%d%d%s+-->%s+") then
      vim.fn.setline(lnum, line .. last_timestamp)
      break
    end
    lnum = lnum + 1
  end
end


local function MainLoop()
  local n = vim.v.count1
  if n < 2 then
    return
  elseif n == 2 then
    DelFirstParagraph()
    DelLastParagraph()
  else
    DelFirstParagraph()
    for _ = 1, n - 2 do
      DelParagraph()
    end
    DelLastParagraph()
  end
end

vim.keymap.set('n', 'd', MainLoop, { noremap = true, silent = true })
