import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import CandidateLayer from './CandidateLayer';

function renderCandidate(overrides = {}) {
  const props = {
    metricKey: 'hugo',
    label: 'Hugo Leal',
    color: '#8B4A9C',
    visible: true,
    onToggleVisible: vi.fn(),
    count: '265',
    years: [2018, 2022],
    selectedYear: 2022,
    onYearChange: vi.fn(),
    pairs: ['2018-2022'],
    isComparing: false,
    onToggleCompare: vi.fn(),
    selectedPair: null,
    onSelectPair: vi.fn(),
    deltaTotal: null,
    pairMeta: null,
    ...overrides,
  };
  const utils = render(<CandidateLayer {...props} />);
  return { ...utils, props };
}

describe('CandidateLayer', () => {
  it('shows the candidate name, dot color, and count in the summary row', () => {
    const { container } = renderCandidate();
    expect(screen.getByText('Hugo Leal')).toBeInTheDocument();
    expect(screen.getByText('265')).toBeInTheDocument();
    expect(container.querySelector('.layer-dot').style.background).toBe('rgb(139, 74, 156)');
  });

  it('toggles visibility via the summary-row checkbox', () => {
    const { props } = renderCandidate();
    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    expect(props.onToggleVisible).toHaveBeenCalledTimes(1);
  });

  it("renders that candidate's own year chips, not a shared global list", () => {
    renderCandidate({ years: [2010, 2014, 2018, 2022], selectedYear: 2022 });
    expect(screen.getByText('Todos')).toBeInTheDocument();
    expect(screen.getByText('2010')).toBeInTheDocument();
    expect(screen.getByText('2022')).toHaveClass('active');
  });

  it('calls onYearChange with the clicked year, and with null for "Todos"', () => {
    const { props } = renderCandidate({ years: [2018, 2022] });
    fireEvent.click(screen.getByText('2018'));
    expect(props.onYearChange).toHaveBeenCalledWith(2018);
    fireEvent.click(screen.getByText('Todos'));
    expect(props.onYearChange).toHaveBeenCalledWith(null);
  });

  it('hides the pair chips until "Comparar dois anos" is on', () => {
    renderCandidate({ isComparing: false, pairs: ['2018-2022'] });
    expect(screen.queryByText('2018-2022')).not.toBeInTheDocument();
  });

  it('reveals this candidate\'s own valid pairs, the delta total, and the cargo-diferente flag once comparing', () => {
    renderCandidate({
      isComparing: true,
      pairs: ['2018-2022'],
      selectedPair: '2018-2022',
      deltaTotal: 42,
      pairMeta: { tipo_par: 'Geral -> Geral', cargoDiferente: true },
    });
    expect(screen.getByText('2018-2022')).toHaveClass('active');
    expect(screen.getByText('+42')).toBeInTheDocument();
    expect(screen.getByText('cargo diferente')).toBeInTheDocument();
  });

  it('calls onToggleCompare with this candidate\'s metric key when the checkbox is clicked', () => {
    const { container, props } = renderCandidate();
    const toggle = within(container.querySelector('.delta-toggle-row')).getByRole('checkbox');
    fireEvent.click(toggle);
    expect(props.onToggleCompare).toHaveBeenCalledWith('hugo');
  });

  it('calls onSelectPair with the clicked pair string', () => {
    const { props } = renderCandidate({ isComparing: true, pairs: ['2018-2022', '2014-2018'] });
    fireEvent.click(screen.getByText('2014-2018'));
    expect(props.onSelectPair).toHaveBeenCalledWith('2014-2018');
  });
});
