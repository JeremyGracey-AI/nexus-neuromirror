import { describe, it, expect } from 'vitest';
import { normalize, coreLabel, matchAlias, findChannel, containsToken } from '../lib/labels.js';

describe('label normalization', () => {
  it('lowercases and strips separators', () => {
    expect(normalize('EEG Fz-A1A2')).toBe('eegfza1a2');
    expect(normalize(' Fz ')).toBe('fz');
  });

  it('coreLabel strips EEG prefix and reference suffixes', () => {
    expect(coreLabel('EEG Fz-A1A2')).toBe('fz');
    expect(coreLabel('Pz-LE')).toBe('pz');
    expect(coreLabel('Oz-A1A2')).toBe('oz');
  });
});

describe('alias matching', () => {
  const fzAliases = ['Fz', 'EEG Fz', 'Fz-A1A2', 'Fz-LE', 'Ch1', 'A-Fz'];
  it('matches many surface forms of Fz', () => {
    expect(matchAlias('EEG Fz-A1A2', fzAliases)).toBe(true);
    expect(matchAlias('Fz', fzAliases)).toBe(true);
    expect(matchAlias('Ch1', fzAliases)).toBe(true);
    expect(matchAlias('Pz', fzAliases)).toBe(false);
  });

  it('findChannel returns the first matching channel name', () => {
    const names = ['EEG Fz-A1A2', 'EEG Pz-A1A2', 'Status'];
    expect(findChannel(names, fzAliases)).toBe('EEG Fz-A1A2');
    expect(findChannel(names, ['Oz', 'EEG Oz'])).toBeNull();
  });
});

describe('containsToken', () => {
  it('detects marker/status tokens', () => {
    expect(containsToken('Status', ['Status', 'Marker'])).toBe(true);
    expect(containsToken('Trigger channel', ['trigger'])).toBe(true);
    expect(containsToken('EEG Fz', ['status'])).toBe(false);
  });
});
