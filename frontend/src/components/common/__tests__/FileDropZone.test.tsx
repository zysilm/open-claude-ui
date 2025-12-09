import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FileDropZone from '../FileDropZone';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Upload: () => <div data-testid="upload-icon" />,
  FileUp: () => <div data-testid="file-up-icon" />,
  Loader2: () => <div data-testid="loader-icon" />,
}));

describe('FileDropZone', () => {
  const mockOnUpload = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderDropZone = (props = {}) => {
    return render(
      <FileDropZone onUpload={mockOnUpload} {...props} />
    );
  };

  it('should render with default text', () => {
    renderDropZone();

    expect(screen.getByText(/Drag and drop a file here/)).toBeInTheDocument();
    expect(screen.getByText(/click to browse/)).toBeInTheDocument();
  });

  it('should render in compact mode', () => {
    renderDropZone({ compact: true });

    expect(screen.getByText(/Drop file or click to upload/)).toBeInTheDocument();
  });

  it('should show Upload icon in default state', () => {
    renderDropZone();

    expect(screen.getByTestId('upload-icon')).toBeInTheDocument();
  });

  it('should show Loader icon when uploading', () => {
    renderDropZone({ isUploading: true });

    expect(screen.getByTestId('loader-icon')).toBeInTheDocument();
    expect(screen.getByText('Uploading...')).toBeInTheDocument();
  });

  it('should show max size hint', () => {
    renderDropZone({ maxSize: 10 * 1024 * 1024 }); // 10MB

    expect(screen.getByText('Max 10MB')).toBeInTheDocument();
  });

  it('should show max size in KB for small limits', () => {
    renderDropZone({ maxSize: 500 * 1024 }); // 500KB

    expect(screen.getByText('Max 500KB')).toBeInTheDocument();
  });

  it('should call onUpload when file is dropped', async () => {
    mockOnUpload.mockResolvedValueOnce(undefined);
    const { container } = renderDropZone();

    const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
    const dropZone = container.querySelector('.file-drop-zone')!;

    const dataTransfer = {
      files: [file],
      items: [{ kind: 'file', type: 'text/plain' }],
      types: ['Files'],
    };

    fireEvent.drop(dropZone, { dataTransfer });

    await waitFor(() => {
      expect(mockOnUpload).toHaveBeenCalledWith(file);
    });
  });

  it('should not call onUpload when uploading', async () => {
    const { container } = renderDropZone({ isUploading: true });

    const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
    const dropZone = container.querySelector('.file-drop-zone')!;

    const dataTransfer = {
      files: [file],
      items: [{ kind: 'file', type: 'text/plain' }],
      types: ['Files'],
    };

    fireEvent.drop(dropZone, { dataTransfer });

    expect(mockOnUpload).not.toHaveBeenCalled();
  });

  it('should show error when file exceeds max size', async () => {
    renderDropZone({ maxSize: 100 }); // 100 bytes
    const { container } = renderDropZone({ maxSize: 100 });

    const file = new File(['a'.repeat(200)], 'large.txt', { type: 'text/plain' });
    const dropZone = container.querySelector('.file-drop-zone')!;

    const dataTransfer = {
      files: [file],
      items: [{ kind: 'file', type: 'text/plain' }],
      types: ['Files'],
    };

    fireEvent.drop(dropZone, { dataTransfer });

    await waitFor(() => {
      expect(screen.getByText(/File size exceeds/)).toBeInTheDocument();
    });

    expect(mockOnUpload).not.toHaveBeenCalled();
  });

  it('should show error when upload fails', async () => {
    mockOnUpload.mockRejectedValueOnce(new Error('Upload failed'));
    const { container } = renderDropZone();

    const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
    const dropZone = container.querySelector('.file-drop-zone')!;

    const dataTransfer = {
      files: [file],
      items: [{ kind: 'file', type: 'text/plain' }],
      types: ['Files'],
    };

    fireEvent.drop(dropZone, { dataTransfer });

    await waitFor(() => {
      expect(screen.getByText('Upload failed')).toBeInTheDocument();
    });
  });

  it('should handle drag enter and leave events', () => {
    const { container } = renderDropZone();
    const dropZone = container.querySelector('.file-drop-zone')!;

    const dataTransfer = {
      items: [{ kind: 'file' }],
    };

    fireEvent.dragEnter(dropZone, { dataTransfer });

    expect(dropZone).toHaveClass('dragging');

    fireEvent.dragLeave(dropZone, { dataTransfer });

    expect(dropZone).not.toHaveClass('dragging');
  });

  it('should show FileUp icon when dragging', () => {
    const { container } = renderDropZone();
    const dropZone = container.querySelector('.file-drop-zone')!;

    const dataTransfer = {
      items: [{ kind: 'file' }],
    };

    fireEvent.dragEnter(dropZone, { dataTransfer });

    expect(screen.getByTestId('file-up-icon')).toBeInTheDocument();
    expect(screen.getByText('Drop file here')).toBeInTheDocument();
  });

  it('should handle file selection via input', async () => {
    mockOnUpload.mockResolvedValueOnce(undefined);
    const { container } = renderDropZone();

    const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
    const input = container.querySelector('input[type="file"]')!;

    Object.defineProperty(input, 'files', { value: [file] });
    fireEvent.change(input);

    await waitFor(() => {
      expect(mockOnUpload).toHaveBeenCalledWith(file);
    });
  });

  it('should apply custom className', () => {
    const { container } = renderDropZone({ className: 'custom-class' });
    const dropZone = container.querySelector('.file-drop-zone');

    expect(dropZone).toHaveClass('custom-class');
  });

  it('should apply accept attribute to input', () => {
    const { container } = renderDropZone({ accept: '.pdf,.doc' });
    const input = container.querySelector('input[type="file"]');

    expect(input).toHaveAttribute('accept', '.pdf,.doc');
  });

  it('should have hidden file input', () => {
    const { container } = renderDropZone();
    const input = container.querySelector('input[type="file"]');

    expect(input).toHaveStyle({ display: 'none' });
  });

  it('should not trigger file dialog when uploading', async () => {
    const { container } = renderDropZone({ isUploading: true });
    const dropZone = container.querySelector('.file-drop-zone')!;
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;

    const clickSpy = vi.spyOn(input, 'click');

    await userEvent.click(dropZone);

    expect(clickSpy).not.toHaveBeenCalled();
  });
});
