import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ProjectSearch from '../ProjectSearch';

describe('ProjectSearch', () => {
  it('should render with placeholder text', () => {
    const onChange = vi.fn();
    render(<ProjectSearch value="" onChange={onChange} />);

    const input = screen.getByPlaceholderText('Search projects...');
    expect(input).toBeInTheDocument();
  });

  it('should display the provided value', () => {
    const onChange = vi.fn();
    render(<ProjectSearch value="test search" onChange={onChange} />);

    const input = screen.getByDisplayValue('test search');
    expect(input).toBeInTheDocument();
  });

  it('should call onChange when input value changes', () => {
    const onChange = vi.fn();
    render(<ProjectSearch value="" onChange={onChange} />);

    const input = screen.getByPlaceholderText('Search projects...');
    fireEvent.change(input, { target: { value: 'new value' } });

    expect(onChange).toHaveBeenCalledWith('new value');
  });

  it('should call onChange with empty string when cleared', () => {
    const onChange = vi.fn();
    render(<ProjectSearch value="existing" onChange={onChange} />);

    const input = screen.getByPlaceholderText('Search projects...');
    fireEvent.change(input, { target: { value: '' } });

    expect(onChange).toHaveBeenCalledWith('');
  });

  it('should have correct CSS class', () => {
    const onChange = vi.fn();
    const { container } = render(<ProjectSearch value="" onChange={onChange} />);

    expect(container.querySelector('.project-search')).toBeInTheDocument();
    expect(container.querySelector('.search-input')).toBeInTheDocument();
  });
});
