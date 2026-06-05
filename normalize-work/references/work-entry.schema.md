# normalize-work Output Schema

```ts
interface NormalizeWorkOutput {
  schemaVersion: 1;
  generatedAt: string;
  date: string;
  source: {
    gitSearchInput: string;
    commitCount: number;
  };
  entries: WorkEntry[];
  review: WorkEntry[];
}

interface WorkEntry {
  projectCode: string;
  projectName: string;
  workType: "正常" | "加班" | string;
  hours: string;
  content: string;
  needsReview: boolean;
  reviewReason?: string;
  sources: string[];
}
```
