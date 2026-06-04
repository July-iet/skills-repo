param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d{4}-\d{2}$')]
    [string]$Month,

    [string]$RootPath = 'D:\Projects',

    [string]$OutputDir = '',

    [string[]]$AuthorKeywords = @('叶菁', 'yejing', 'yejing@poweroak', '310100519', 'G310100519'),

    [switch]$UseAI,

    [string]$BaseUrl = 'https://api.deepseek.com',

    [string]$Model = 'deepseek-v4-pro',

    [string]$ApiKeyEnv = 'DEEPSEEK_API_KEY'
)

$ErrorActionPreference = 'Stop'

function Get-ScriptRoot {
    if ($PSScriptRoot) {
        return $PSScriptRoot
    }
    return Split-Path -Parent $MyInvocation.MyCommand.Path
}

function Resolve-DefaultOutputDir {
    param(
        [string]$SkillRoot,
        [string]$MonthLabel
    )

    $workspaceRootPath = Join-Path $SkillRoot '..\..\..'
    $workspaceRoot = Resolve-Path -Path $workspaceRootPath -ErrorAction SilentlyContinue
    if ($workspaceRoot) {
        $monthsRoot = Join-Path $workspaceRoot.Path 'data\months'
        if (Test-Path $monthsRoot) {
            return (Join-Path (Join-Path $monthsRoot $MonthLabel) 'input')
        }
    }

    return $SkillRoot
}

function Resolve-OutputFilePath {
    param([string]$DirectoryPath)

    $index = 0
    while ($true) {
        $fileName = if ($index -eq 0) { 'git_stats.md' } else { "git_stats_$index.md" }
        $candidatePath = Join-Path $DirectoryPath $fileName
        if (-not (Test-Path $candidatePath)) {
            return $candidatePath
        }
        $index++
    }
}

function Get-MonthRange {
    param([string]$TargetMonth)

    $start = [datetime]::ParseExact($TargetMonth + '-01', 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture)
    $end = $start.AddMonths(1)

    [pscustomobject]@{
        Start = $start
        End = $end
        Label = $start.ToString('yyyy-MM')
        Year = $start.Year
        MonthNumber = $start.Month
    }
}

function Invoke-Git {
    param(
        [string]$RepoPath,
        [string[]]$Arguments
    )

    $output = & git -C $RepoPath @Arguments 2>$null
    if ($LASTEXITCODE -ne 0) {
        return @()
    }
    return @($output)
}

function Find-GitRepos {
    param(
        [string]$BasePath,
        [string[]]$ExcludeNames
    )

    Get-ChildItem -Path $BasePath -Directory -Force |
        Where-Object { $ExcludeNames -notcontains $_.Name } |
        Where-Object { Test-Path (Join-Path $_.FullName '.git') } |
        Sort-Object Name
}

function Test-AuthorMatched {
    param(
        [string[]]$Values,
        [string[]]$Keywords
    )

    foreach ($value in $Values) {
        foreach ($keyword in $Keywords) {
            if (-not [string]::IsNullOrWhiteSpace($value) -and $value.IndexOf($keyword, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
                return $true
            }
        }
    }
    return $false
}

function Format-CommitTime {
    param([string]$IsoTime)

    $offset = [datetimeoffset]::Parse($IsoTime)
    return $offset.ToString('yyyy-MM-dd HH:mm:ss zzz')
}

function Get-CommitStats {
    param(
        [string]$RepoPath,
        [string]$Hash
    )

    $lines = Invoke-Git -RepoPath $RepoPath -Arguments @('show', '--numstat', '--format=', '--no-renames', $Hash)
    $fileCount = 0
    $insertions = 0
    $deletions = 0
    $paths = New-Object System.Collections.Generic.List[string]

    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $parts = $line -split "`t"
        if ($parts.Count -lt 3) {
            continue
        }

        $fileCount++
        if ($parts[0] -match '^\d+$') {
            $insertions += [int]$parts[0]
        }
        if ($parts[1] -match '^\d+$') {
            $deletions += [int]$parts[1]
        }
        $paths.Add($parts[2])
    }

    [pscustomobject]@{
        FileCount = $fileCount
        Insertions = $insertions
        Deletions = $deletions
        Paths = @($paths)
    }
}

function Get-CommitBranch {
    param(
        [string]$RepoPath,
        [string]$Hash
    )

    $refs = Invoke-Git -RepoPath $RepoPath -Arguments @('branch', '--all', '--contains', $Hash, '--format=%(refname)')
    $remoteRefs = New-Object System.Collections.Generic.List[string]
    $localRefs = New-Object System.Collections.Generic.List[string]

    foreach ($ref in $refs) {
        if ($ref -like 'refs/remotes/*' -and $ref -notlike '*/HEAD') {
            $remoteRefs.Add(($ref -replace '^refs/remotes/', ''))
        }
        elseif ($ref -like 'refs/heads/*') {
            $localRefs.Add(($ref -replace '^refs/heads/', ''))
        }
    }

    if ($remoteRefs.Count -gt 0) {
        return ($remoteRefs | Sort-Object | Select-Object -First 1)
    }
    if ($localRefs.Count -gt 0) {
        return ($localRefs | Sort-Object | Select-Object -First 1)
    }

    $fallbacks = @(
        (Invoke-Git -RepoPath $RepoPath -Arguments @('branch', '--show-current') | Select-Object -First 1),
        'origin/develop',
        'origin/master',
        'origin/main',
        'develop',
        'master',
        'main'
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

    foreach ($branch in $fallbacks) {
        $exists = Invoke-Git -RepoPath $RepoPath -Arguments @('rev-parse', '--verify', $branch)
        if ($exists.Count -gt 0) {
            return $branch
        }
    }

    return '未识别分支'
}

function Get-CommitTopic {
    param(
        [string]$Subject,
        [string[]]$Paths
    )

    $text = ($Subject + ' ' + ($Paths -join ' ')).ToLowerInvariant()

    if ($Subject -match '^(Merge|merge)\b') { return '分支合并与代码同步' }
    if ($text -match '打包|发版|发布|dist|build') { return '版本打包与环境发布处理' }
    if ($text -match 'fix|修复|bug|报错|问题') { return '缺陷修复与稳定性处理' }
    if ($text -match '国际化|i18n|文案|locale|locales') { return '国际化文案与界面展示优化' }
    if ($text -match '权限|隐藏|字段|可见') { return '字段权限与页面可见性收敛' }
    if ($text -match '订单审核|审批|拒绝原因') { return '订单审核流程与审批交互完善' }
    if ($text -match '订单|支付|库存|客户') { return '订单模块字段、详情与交易信息完善' }
    if ($text -match '流程|看板|待办|任务|需求') { return '流程配置与流程看板能力增强' }
    if ($text -match '附件|下载|视频|icon|图标') { return '附件与下载链路优化' }
    if ($text -match '样式|布局|弹窗|按钮|交互') { return '页面布局与交互优化' }
    if ($text -match '发票|netsuite|sku|msku') { return 'NetSuite 脚本与业务规则调整' }

    return '功能开发与细节优化'
}

function ConvertTo-CommitItem {
    param(
        [string]$RepoName,
        [string]$RepoPath,
        [string]$LogLine,
        [string[]]$Keywords
    )

    $parts = $LogLine -split [char]0x1f
    if ($parts.Count -lt 7) {
        return $null
    }

    $hash = $parts[0]
    $authorDate = $parts[1]
    $authorName = $parts[2]
    $authorEmail = $parts[3]
    $committerName = $parts[4]
    $committerEmail = $parts[5]
    $subject = $parts[6]

    $matched = Test-AuthorMatched -Values @($authorName, $authorEmail, $committerName, $committerEmail) -Keywords $Keywords
    if (-not $matched) {
        return $null
    }

    $stats = Get-CommitStats -RepoPath $RepoPath -Hash $hash
    $branch = Get-CommitBranch -RepoPath $RepoPath -Hash $hash
    $topic = Get-CommitTopic -Subject $subject -Paths $stats.Paths

    [pscustomobject]@{
        Project = $RepoName
        Branch = $branch
        Hash = $hash
        ShortHash = $hash.Substring(0, [Math]::Min(8, $hash.Length))
        CommitTime = Format-CommitTime -IsoTime $authorDate
        CommitDate = ([datetimeoffset]::Parse($authorDate)).Date.ToString('yyyy-MM-dd')
        Author = "$authorName <$authorEmail>"
        Committer = "$committerName <$committerEmail>"
        Subject = $subject
        FileCount = $stats.FileCount
        Insertions = $stats.Insertions
        Deletions = $stats.Deletions
        Paths = $stats.Paths
        Topic = $topic
        Summary = "$topic（涉及 $($stats.FileCount) 个文件，+$($stats.Insertions)/-$($stats.Deletions)）"
    }
}

function Get-CommitsForRepo {
    param(
        [System.IO.DirectoryInfo]$Repo,
        [datetime]$Start,
        [datetime]$End,
        [string[]]$Keywords
    )

    $since = $Start.ToString('yyyy-MM-dd HH:mm:ss')
    $before = $End.ToString('yyyy-MM-dd HH:mm:ss')
    $format = '%H%x1f%aI%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%s'
    $logLines = Invoke-Git -RepoPath $Repo.FullName -Arguments @('log', '--branches', '--remotes', "--since=$since", "--before=$before", "--format=$format")
    $items = New-Object System.Collections.Generic.List[object]
    $seen = @{}

    foreach ($line in $logLines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $hash = ($line -split [char]0x1f)[0]
        if ($seen.ContainsKey($hash)) {
            continue
        }
        $seen[$hash] = $true

        $item = ConvertTo-CommitItem -RepoName $Repo.Name -RepoPath $Repo.FullName -LogLine $line -Keywords $Keywords
        if ($null -ne $item) {
            $items.Add($item)
        }
    }

    return @($items.ToArray())
}

function Get-ProjectStats {
    param([object[]]$CommitItems)

    $CommitItems |
        Group-Object Project |
        ForEach-Object {
            [pscustomobject]@{
                Project = $_.Name
                Commits = $_.Group.Count
                Insertions = ($_.Group | Measure-Object Insertions -Sum).Sum
                Deletions = ($_.Group | Measure-Object Deletions -Sum).Sum
                FileChanges = ($_.Group | Measure-Object FileCount -Sum).Sum
                UniqueFiles = ($_.Group.Paths | Sort-Object -Unique).Count
            }
        } |
        Sort-Object @{ Expression = 'Commits'; Descending = $true }, Project
}

function Get-BranchStats {
    param([object[]]$CommitItems)

    $CommitItems |
        Group-Object Project, Branch |
        ForEach-Object {
            $first = $_.Group | Select-Object -First 1
            [pscustomobject]@{
                Project = $first.Project
                Branch = $first.Branch
                Commits = $_.Group.Count
                Insertions = ($_.Group | Measure-Object Insertions -Sum).Sum
                Deletions = ($_.Group | Measure-Object Deletions -Sum).Sum
            }
        } |
        Sort-Object Project, Branch
}

function New-AiContext {
    param(
        [object]$Range,
        [string]$RootPath,
        [string[]]$Keywords,
        [object[]]$CommitItems,
        [object[]]$ProjectStats,
        [object[]]$BranchStats
    )

    $actualAuthors = $CommitItems.Author | Sort-Object -Unique
    $topicGroups = $CommitItems |
        Group-Object Topic |
        Sort-Object Count -Descending |
        ForEach-Object {
            [pscustomobject]@{
                topic = $_.Name
                commits = $_.Count
                projects = @($_.Group.Project | Sort-Object -Unique)
            }
        }

    [pscustomobject]@{
        report_month = $Range.Label
        author_keywords = $Keywords
        actual_authors = @($actualAuthors)
        time_range = [pscustomobject]@{
            start = $Range.Start.ToString('yyyy-MM-dd 00:00:00')
            end = $Range.End.ToString('yyyy-MM-dd 00:00:00')
        }
        scope = [pscustomobject]@{
            root_path = $RootPath
            excluded_dirs = @('auto-git')
            branches = '--branches --remotes'
        }
        totals = [pscustomobject]@{
            commits = $CommitItems.Count
            projects = ($CommitItems.Project | Sort-Object -Unique).Count
            active_days = ($CommitItems.CommitDate | Sort-Object -Unique).Count
            file_changes = ($CommitItems | Measure-Object FileCount -Sum).Sum
            unique_files = ($CommitItems.Paths | Sort-Object -Unique).Count
            insertions = ($CommitItems | Measure-Object Insertions -Sum).Sum
            deletions = ($CommitItems | Measure-Object Deletions -Sum).Sum
        }
        project_stats = @($ProjectStats)
        branch_stats = @($BranchStats)
        topic_groups = @($topicGroups)
        commit_items = @($CommitItems | Sort-Object Project, Branch, CommitTime | ForEach-Object {
            [pscustomobject]@{
                project = $_.Project
                branch = $_.Branch
                short_hash = $_.ShortHash
                commit_time = $_.CommitTime
                subject = $_.Subject
                file_count = $_.FileCount
                insertions = $_.Insertions
                deletions = $_.Deletions
                topic = $_.Topic
                summary = $_.Summary
            }
        })
    }
}

function Invoke-DeepSeekSummary {
    param(
        [string]$PromptPath,
        [string]$RulesPath,
        [string]$ExamplesPath,
        [object]$Context,
        [string]$ApiBaseUrl,
        [string]$AiModel,
        [string]$KeyEnvName
    )

    $apiKey = [Environment]::GetEnvironmentVariable($KeyEnvName, 'Process')
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        $apiKey = [Environment]::GetEnvironmentVariable($KeyEnvName, 'User')
    }
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        $apiKey = [Environment]::GetEnvironmentVariable($KeyEnvName, 'Machine')
    }
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        throw "未找到环境变量 $KeyEnvName，请先设置 DeepSeek API Key。"
    }

    $prompt = Get-Content -Path $PromptPath -Raw -Encoding UTF8
    $rules = Get-Content -Path $RulesPath -Raw -Encoding UTF8
    $examples = Get-Content -Path $ExamplesPath -Raw -Encoding UTF8
    $contextJson = $Context | ConvertTo-Json -Depth 12 -Compress
    $userContent = @"
以下是固定 Prompt：
$prompt

以下是 Rules：
$rules

以下是 Few-shot 样例：
$examples

以下是本次 Git 统计 JSON：
$contextJson
"@

    $bodyJson = [pscustomobject]@{
        model = $AiModel
        temperature = 0.2
        messages = @(
            [pscustomobject]@{
                role = 'system'
                content = "你必须严格遵守固定 Prompt、Rules 和 Few-shot 样例，只基于输入 JSON 生成 Markdown。"
            },
            [pscustomobject]@{
                role = 'user'
                content = $userContent
            }
        )
    } | ConvertTo-Json -Depth 12 -Compress
    $null = $bodyJson | ConvertFrom-Json
    $bodyBytes = [Text.Encoding]::UTF8.GetBytes($bodyJson)

    $uri = "$($ApiBaseUrl.TrimEnd('/'))/chat/completions"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Write-Host "AI request size: $([Math]::Round($bodyBytes.Length / 1KB, 2)) KB"

    $tempBodyPath = Join-Path ([IO.Path]::GetTempPath()) ("deepseek-request-{0}.json" -f ([guid]::NewGuid().ToString('N')))
    [IO.File]::WriteAllText($tempBodyPath, $bodyJson, [Text.UTF8Encoding]::new($false))
    try {
        $curlOutput = & curl.exe -sS -X POST $uri `
            -H "Authorization: Bearer $apiKey" `
            -H 'Content-Type: application/json; charset=utf-8' `
            --data-binary "@$tempBodyPath" `
            -w "`n__HTTP_STATUS__:%{http_code}"

        if ($LASTEXITCODE -ne 0) {
            throw "DeepSeek API 请求失败：curl 退出码 $LASTEXITCODE。$curlOutput"
        }

        $rawResponse = ($curlOutput -join "`n")
        $statusMarker = "`n__HTTP_STATUS__:"
        $markerIndex = $rawResponse.LastIndexOf($statusMarker, [StringComparison]::Ordinal)
        if ($markerIndex -lt 0) {
            throw "DeepSeek API 响应缺少 HTTP 状态码。$rawResponse"
        }

        $responseText = $rawResponse.Substring(0, $markerIndex)
        $statusCode = [int]$rawResponse.Substring($markerIndex + $statusMarker.Length)

        if ($statusCode -lt 200 -or $statusCode -ge 300) {
            throw "DeepSeek API 请求失败：HTTP $statusCode。$responseText"
        }

        $response = $responseText | ConvertFrom-Json
        return $response.choices[0].message.content.Trim()
    }
    finally {
        if (Test-Path $tempBodyPath) {
            Remove-Item -Path $tempBodyPath -Force
        }
    }
}

function New-ProjectDistributionMarkdown {
    param([object[]]$ProjectStats)

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('## 项目分布')
    $lines.Add('')
    $lines.Add('| 项目 | 提交次数 | 新增行数 | 删除行数 |')
    $lines.Add('| --- | ---: | ---: | ---: |')
    foreach ($stat in $ProjectStats) {
        $lines.Add("| $($stat.Project) | $($stat.Commits) | $($stat.Insertions) | $($stat.Deletions) |")
    }
    return ($lines -join "`r`n")
}

$scriptRoot = Get-ScriptRoot
$skillRoot = Split-Path -Parent $scriptRoot
$shouldUseAI = if ($PSBoundParameters.ContainsKey('UseAI')) { [bool]$UseAI } else { $true }
$range = Get-MonthRange -TargetMonth $Month
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Resolve-DefaultOutputDir -SkillRoot $skillRoot -MonthLabel $range.Label
}
$repos = Find-GitRepos -BasePath $RootPath -ExcludeNames @('auto-git')
$allCommits = New-Object System.Collections.Generic.List[object]

foreach ($repo in $repos) {
    Write-Host "Scanning $($repo.Name)..."
    $repoCommits = Get-CommitsForRepo -Repo $repo -Start $range.Start -End $range.End -Keywords $AuthorKeywords
    foreach ($commit in $repoCommits) {
        $allCommits.Add($commit)
    }
}

$commitItems = @($allCommits | Sort-Object Project, Branch, CommitTime)
$projectStats = @(Get-ProjectStats -CommitItems $commitItems)
$branchStats = @(Get-BranchStats -CommitItems $commitItems)
$context = New-AiContext -Range $range -RootPath $RootPath -Keywords $AuthorKeywords -CommitItems $commitItems -ProjectStats $projectStats -BranchStats $branchStats

$promptPath = Join-Path $skillRoot 'references\monthly-report.prompt.md'
$rulesPath = Join-Path $skillRoot 'references\monthly-report.rules.md'
$examplesPath = Join-Path $skillRoot 'references\monthly-report.examples.md'

if ($shouldUseAI) {
    Write-Host "Calling DeepSeek model $Model..."
    $aiMarkdown = Invoke-DeepSeekSummary -PromptPath $promptPath -RulesPath $rulesPath -ExamplesPath $examplesPath -Context $context -ApiBaseUrl $BaseUrl -AiModel $Model -KeyEnvName $ApiKeyEnv
}
else {
    $aiMarkdown = "## 第一部分：提交明细`r`n`r`n未启用 AI，未生成提交明细正文。`r`n`r`n## 第二部分：当月工作内容总结`r`n`r`n### 事实版总结`r`n`r`n未启用 AI。`r`n`r`n### KPI 量化版总结`r`n`r`n未启用 AI。"
}

$totalInsertions = ($commitItems | Measure-Object Insertions -Sum).Sum
$totalDeletions = ($commitItems | Measure-Object Deletions -Sum).Sum
$uniqueFiles = ($commitItems.Paths | Sort-Object -Unique).Count
$actualAuthors = ($commitItems.Author | Sort-Object -Unique) -join '；'
$tick = [char]96
$startText = $range.Start.ToString('yyyy-MM-dd 00:00:00')
$endText = $range.End.ToString('yyyy-MM-dd 00:00:00')
$authorText = $AuthorKeywords -join ' / '
$projectCount = ($commitItems.Project | Sort-Object -Unique).Count

$header = @"
# $($range.Year) 年 $($range.MonthNumber) 月 Git 工作汇总

## 统计说明

- 统计范围：$tick$RootPath$tick 根目录下所有 Git 项目，排除 ${tick}auto-git$tick，遍历本地/远程分支（${tick}--branches --remotes$tick）。
- 统计时间：$tick$startText$tick 至 $tick$endText$tick。
- 作者匹配：按作者名/邮箱关键字匹配 $tick$authorText$tick；本次实际命中的作者为 $tick$actualAuthors$tick。
- 结果概览：共命中 $tick$($commitItems.Count)$tick 次提交，覆盖 $tick$projectCount$tick 个项目；新增 $tick$totalInsertions$tick 行，删除 $tick$totalDeletions$tick 行，涉及 $tick$uniqueFiles$tick 个唯一文件。

"@

$distribution = New-ProjectDistributionMarkdown -ProjectStats $projectStats
$report = $header + $aiMarkdown + "`r`n`r`n" + $distribution + "`r`n"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$outputPath = Resolve-OutputFilePath -DirectoryPath $OutputDir
Set-Content -Path $outputPath -Value $report -Encoding UTF8

Write-Host "Report generated: $outputPath"
