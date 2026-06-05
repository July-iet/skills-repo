# git-search JSON Schema

```ts
interface GitSearchOutput {
  schemaVersion: 1;
  generatedAt: string;
  query: GitSearchQuery;
  totals: GitTotals;
  projectStats: ProjectStat[];
  branchStats: BranchStat[];
  topicGroups: TopicGroup[];
  commits: CommitSummary[];
  warnings: Warning[];
}

interface CommitSummary {
  repo: string;
  repoPath: string;
  branch: string;
  hash: string;
  shortHash: string;
  commitTime: string;
  commitDate: string;
  authorName: string;
  authorEmail: string;
  committerName: string;
  committerEmail: string;
  subject: string;
  fileCount: number;
  insertions: number;
  deletions: number;
  paths: string[];
  topic: string;
  summary: string;
}
```

Stability rules:

- `commits` is sorted by `repo`, `branch`, `commitTime`, and `hash`.
- The time range is left-closed and right-open.
- One commit is counted once per repository by full hash.
- `branch` is a single classified branch chosen from containing refs.
