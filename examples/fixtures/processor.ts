import { EventEmitter } from 'events';
import fs from 'fs';

export class DataProcessor extends EventEmitter {
  private name: string;

  constructor(name: string) {
    super();
    this.name = name;
  }

  process(data: string[]): string[] {
    return data.map(d => d.trim());
  }

  async fetchAndProcess(url: string): Promise<string[]> {
    const raw = await fetch(url).then(r => r.text());
    return this.process(raw.split('\n'));
  }
}

export function formatOutput(items: string[]): string {
  return items.join('\n');
}
