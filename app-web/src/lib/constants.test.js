import { describe, it, expect } from 'vitest';
import { COLORS, LABELS, BASE_KEYS } from './constants';

describe('COLORS', () => {
  it('assigns the DESIGN2 candidate identity colors (Hugo warmed to sit on eggshell paper)', () => {
    expect(COLORS.hugo_leal).toBe('#8B4A9C');
    expect(COLORS.felipe_peixoto).toBe('#1B7952');
    expect(COLORS.psd).toBe('#1E3A5F');
  });

  it('exposes the PSD secondary brand colors for a future chapa breakdown chart', () => {
    expect(COLORS.psdOlive).toBe('#6E7B3D');
    expect(COLORS.psdOrange).toBe('#E07A1F');
  });

  it('uses a colorblind-safe red-teal diverging scale, not red-green', () => {
    expect(COLORS.deltaLoss).toBe('#B91C1C');
    expect(COLORS.deltaNeutral).toBe('#EDEFF2');
    expect(COLORS.deltaGain).toBe('#0F766E');
  });

  it('exposes the profile/demographic sequential-scale accent', () => {
    expect(COLORS.profileAccent).toBe('#312E81');
  });

  it('gives the Municipal/Geral year-type dots colors distinct from candidate and delta colors', () => {
    expect(COLORS.yearMunicipal).toBe('#CA8A04');
    expect(COLORS.yearGeral).toBe('#BE185D');
  });

  it('keeps every BASE_KEYS entry covered by both COLORS and LABELS', () => {
    BASE_KEYS.forEach(key => {
      expect(COLORS[key]).toBeDefined();
      expect(LABELS[key]).toBeDefined();
    });
  });
});
