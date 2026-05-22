export interface HNStory {
  id: number;
  title: string;
  score: number;
  by: string;
  url?: string;
  descendants?: number;
  time?: string;
  hn_url?: string;
}

export interface ActiveToolCall {
  id: string;
  name: string;
  args: string;
  result?: string;
  finished: boolean;
}
