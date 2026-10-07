import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CompareTable from './CompareTable';

const data = {
  hugo_leal: { features: [
    { properties: { nr_local: '10', ano: 2018, QT_VOTOS: 40 } },
    { properties: { nr_local: '10', ano: 2022, QT_VOTOS: 60 } },
  ] },
  felipe_peixoto: { features: [
    { properties: { nr_local: '10', ano: 2022, QT_VOTOS: 200 } },
  ] },
  psd: { features: [] },
};

describe('CompareTable', () => {
  it('renders nothing when there is no selection', () => {
    const { container } = render(<CompareTable selection={null} data={data} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders a row per candidate with data at the selected local, one column per year', () => {
    render(<CompareTable selection={{ props: { nr_local: '10', nm_local: 'Escola Teste' }, coords: [1, 2] }} data={data} />);
    expect(screen.getByText('Escola Teste')).toBeInTheDocument();
    expect(screen.getByText('Hugo Leal')).toBeInTheDocument();
    expect(screen.getByText('Felipe Peixoto')).toBeInTheDocument();
    expect(screen.queryByText('PSD')).not.toBeInTheDocument();
    expect(screen.getByText('2018')).toBeInTheDocument();
    expect(screen.getByText('40')).toBeInTheDocument();
    expect(screen.getByText('200')).toBeInTheDocument();
  });

  it('renders nothing when the selected local has no data in any layer', () => {
    const { container } = render(<CompareTable selection={{ props: { nr_local: '999' }, coords: [1, 2] }} data={data} />);
    expect(container).toBeEmptyDOMElement();
  });
});
