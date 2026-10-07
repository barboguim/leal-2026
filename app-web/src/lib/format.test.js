import { describe, it, expect } from 'vitest';
import { electionType, electionPairLabel, formatSigned, formatPct } from './format';

describe('electionType', () => {
  it('classifies years divisible by 4 as Municipal', () => {
    expect(electionType(2012)).toBe('Municipal');
    expect(electionType(2016)).toBe('Municipal');
    expect(electionType(2020)).toBe('Municipal');
    expect(electionType(2024)).toBe('Municipal');
  });

  it('classifies years not divisible by 4 as Geral', () => {
    expect(electionType(2010)).toBe('Geral');
    expect(electionType(2014)).toBe('Geral');
    expect(electionType(2018)).toBe('Geral');
    expect(electionType(2022)).toBe('Geral');
  });
});

describe('electionPairLabel', () => {
  it('labels a municipal-to-geral pair correctly', () => {
    // Regression case: 2012 is Municipal, 2014 is Geral — this exact pair
    // exposed a fixture bug in the Python-side test suite for the same
    // election-type math earlier in this project; covering it here too.
    expect(electionPairLabel(2012, 2014)).toBe('Municipal -> Geral');
  });

  it('labels a geral-to-geral pair correctly', () => {
    expect(electionPairLabel(2010, 2014)).toBe('Geral -> Geral');
  });

  it('labels a municipal-to-municipal pair correctly', () => {
    expect(electionPairLabel(2020, 2024)).toBe('Municipal -> Municipal');
  });
});

describe('formatSigned', () => {
  it('prefixes positive values with +', () => {
    expect(formatSigned(42)).toBe('+42');
  });

  it('leaves negative values as-is', () => {
    expect(formatSigned(-42)).toBe('-42');
  });

  it('formats zero without a sign', () => {
    expect(formatSigned(0)).toBe('0');
  });

  it('formats large numbers with pt-BR thousands separators', () => {
    expect(formatSigned(12345)).toBe('+12.345');
  });

  it('treats non-numeric input as zero', () => {
    expect(formatSigned(undefined)).toBe('0');
    expect(formatSigned(null)).toBe('0');
  });
});

describe('formatPct', () => {
  it('prefixes positive percentages with +', () => {
    expect(formatPct(12.3)).toBe('+12,3%');
  });

  it('leaves negative percentages as-is', () => {
    expect(formatPct(-5)).toBe('-5%');
  });

  it('returns a dash for non-finite input', () => {
    expect(formatPct(NaN)).toBe('-');
    expect(formatPct(undefined)).toBe('-');
  });
});
