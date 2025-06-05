vim.keymap.set('n', '<Insert>', 'i', { noremap = true, silent = true })


local timestamp_pattern = "^%d%d:%d%d:%d%d,%d%d%d%s+-->%s+%d%d:%d%d:%d%d,%d%d%d$"
local single_number_pattern = "^%d+$"

-- Static variable to store where cursor was when command issued
local cursor_initial_pos

local function ClearBlankLines(start_line, end_line)
  -- Jump to start of paragraph
  vim.cmd('normal! {')
  local start_line = vim.fn.line('.')
  -- Find end of paragraph
  vim.cmd('normal! }')
  local end_line = vim.fn.line('.')
  -- Check that there are at least three lines in paragraph
  -- Should be number, timestamp, and subtitle content
  -- Otherwise, skip
  -- TODO: Impelement above comment

  -- Delete blank lines in the paragraph
  lnum = start_line
  while vim.fn.getline(lnum):match("^%s*$") and lnum <= vim.fn.line('$') do
    vim.fn.deletebufline('%', lnum)
    -- Do not increment lnum, as lines shift up
    end_line = end_line - 1
  end
end


local function ReplaceEmptySubtitle()
  local bufnr = vim.api.nvim_get_current_buf()
  local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
  local timestamp_pattern = "^%d%d:%d%d:%d%d,%d%d%d%s+-->%s+%d%d:%d%d:%d%d,%d%d%d$"

  for i = 1, #lines - 1 do
    if lines[i]:match(timestamp_pattern) and lines[i + 1]:match("^%s*$") then
      vim.api.nvim_buf_set_lines(bufnr, i, i + 1, false, { "`" })
    end
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


local function JoinLines()
  -- Jump to start and end of paragraph
  vim.cmd('normal! {')
  local start_line = vim.fn.line('.')
  vim.cmd('normal! }')
  local end_line = vim.fn.line('.')
  if start_line > end_line then start_line, end_line = end_line, start_line end

  local bufnr = vim.api.nvim_get_current_buf()
  local ts_line = nil

  -- Find the timestamp line
  for lnum = start_line, end_line do
    local line = vim.api.nvim_buf_get_lines(bufnr, lnum - 1, lnum, false)[1]
    if line and line:match(timestamp_pattern) then
      ts_line = lnum
      break
    end
  end
  if not ts_line then
    return
  end

  -- Concatenate lines after timestamp in the paragraph, separated by space
  local concat = {}
  for lnum = ts_line + 1, end_line do
    local line = vim.api.nvim_buf_get_lines(bufnr, lnum - 1, lnum, false)[1]
    if line then
      local trimmed = line:match("^%s*(.-)%s*$")
      table.insert(concat, trimmed)
    end
  end

  local joined = table.concat(concat, " ")
  -- Replace the lines after timestamp with the concatenated line
  if #concat > 0 then
    vim.api.nvim_buf_set_lines(bufnr, ts_line, end_line, false, { joined })
  end
end


local function MainLoop()
  -- Save initial line number
  local pos = vim.api.nvim_win_get_cursor(0)
  last_line = pos[1]

  -- Save number of paragraphs to concat
  local n = vim.v.count1

  ReplaceEmptySubtitle()

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
  -- Return cursor to initial position (original paragraph)
  vim.api.nvim_win_set_cursor(0, {last_line, 0})
  JoinLines()
end

vim.keymap.set('n', 'c', MainLoop, { noremap = true, silent = true })
