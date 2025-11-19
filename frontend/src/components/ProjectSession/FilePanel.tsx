import { useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { filesAPI } from '@/services/api';
import './FilePanel.css';

interface FilePanelProps {
  projectId: string;
}

export default function FilePanel({ projectId }: FilePanelProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch files
  const { data: filesData, isLoading } = useQuery({
    queryKey: ['files', projectId],
    queryFn: () => filesAPI.list(projectId),
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => filesAPI.upload(projectId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files', projectId] });
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: filesAPI.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files', projectId] });
    },
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadMutation.mutate(file);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleDelete = (fileId: string) => {
    if (confirm('Delete this file?')) {
      deleteMutation.mutate(fileId);
    }
  };

  const handleDownload = async (fileId: string, filename: string) => {
    try {
      const blob = await filesAPI.download(fileId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const files = filesData?.files || [];

  return (
    <div className="file-panel">
      <div className="file-panel-header">
        <button
          className="upload-btn"
          onClick={handleUploadClick}
          disabled={uploadMutation.isPending}
        >
          {uploadMutation.isPending ? 'Uploading...' : '+ Upload'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />
      </div>

      <div className="file-list">
        {isLoading && <div className="file-list-empty">Loading files...</div>}

        {files.length === 0 && !isLoading && (
          <div className="file-list-empty">
            No files uploaded yet. Upload files to share with the agent.
          </div>
        )}

        {files.map((file: any) => (
          <div key={file.id} className="file-item">
            <div className="file-info">
              <div className="file-name">{file.filename}</div>
              <div className="file-meta">
                {formatFileSize(file.size)} • {file.file_type}
              </div>
            </div>
            <div className="file-actions">
              <button
                className="file-action-btn download"
                onClick={() => handleDownload(file.id, file.filename)}
                title="Download"
              >
                ↓
              </button>
              <button
                className="file-action-btn delete"
                onClick={() => handleDelete(file.id)}
                title="Delete"
              >
                ×
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
