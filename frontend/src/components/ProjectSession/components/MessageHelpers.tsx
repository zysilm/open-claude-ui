import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

export const formatObservationContent = (content: string | any): string => {
  let dataToFormat = content;

  if (typeof content === 'object' && content !== null) {
    dataToFormat = content;
  } else if (typeof content === 'string') {
    try {
      dataToFormat = JSON.parse(content);
    } catch {
      return content.replace(/\\n/g, '\n');
    }
  }

  if (typeof dataToFormat === 'object' && dataToFormat !== null) {
    const resultValue = dataToFormat.result || dataToFormat.output || dataToFormat.data || dataToFormat;

    if (typeof resultValue === 'string') {
      return resultValue.replace(/\\n/g, '\n');
    }

    return JSON.stringify(resultValue, null, 2);
  }

  return String(dataToFormat);
};

export const formatActionArgs = (args: string | any): string => {
  if (typeof args === 'object' && args !== null) {
    return JSON.stringify(args, null, 2);
  }

  if (typeof args === 'string') {
    try {
      const parsed = JSON.parse(args);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return args;
    }
  }

  return String(args);
};

export const getFileExtension = (filePath: string): string => {
  const match = filePath.match(/\.([^.]+)$/);
  return match ? match[1].toLowerCase() : '';
};

export const getLanguageFromExtension = (ext: string): string => {
  const langMap: { [key: string]: string } = {
    'js': 'javascript', 'jsx': 'javascript', 'ts': 'typescript', 'tsx': 'typescript',
    'py': 'python', 'rb': 'ruby', 'java': 'java', 'cpp': 'cpp', 'c': 'c',
    'cs': 'csharp', 'go': 'go', 'rs': 'rust', 'php': 'php', 'swift': 'swift',
    'kt': 'kotlin', 'scala': 'scala', 'sh': 'bash', 'bash': 'bash', 'zsh': 'bash',
    'yml': 'yaml', 'yaml': 'yaml', 'json': 'json', 'xml': 'xml', 'html': 'html',
    'css': 'css', 'scss': 'scss', 'sass': 'sass', 'sql': 'sql',
    'md': 'markdown', 'markdown': 'markdown',
  };
  return langMap[ext] || ext;
};

// ============================================================================
// HELPER COMPONENTS
// ============================================================================

export const CodeBlock = ({ inline, className, children, ...props }: any) => {
  const match = /language-(\w+)/.exec(className || '');
  const language = match ? match[1] : '';

  return !inline && language ? (
    <SyntaxHighlighter
      style={oneLight}
      language={language}
      PreTag="div"
      customStyle={{
        margin: '12px 0',
        borderRadius: '6px',
        border: '1px solid #e5e7eb',
        fontSize: '13px',
      }}
      {...props}
    >
      {String(children).replace(/\n$/, '')}
    </SyntaxHighlighter>
  ) : (
    <code className={className} {...props}>
      {children}
    </code>
  );
};

// Component to render observation content (handles images)
export const ObservationContent = ({ content, metadata }: { content: string | any; metadata?: any }) => {
  // Extract text content from object if needed (for persisted actions)
  let textContent = content;
  if (typeof content === 'object' && content !== null) {
    textContent = content.result || content.output || content.data || JSON.stringify(content);
  }

  // Check if this observation contains an image
  if (metadata && metadata.type === 'image' && metadata.image_data) {
    const imageData = metadata.image_data;
    const filename = metadata.filename || 'image';

    return (
      <div className="observation-content" style={{ textAlign: 'left' }}>
        <div style={{ marginBottom: '12px', color: '#14532d' }}>
          {textContent}
        </div>
        <div style={{
          background: '#ffffff',
          border: '1px solid #86efac',
          borderRadius: '6px',
          padding: '12px',
          textAlign: 'center'
        }}>
          <img
            src={imageData}
            alt={filename}
            style={{
              maxWidth: '100%',
              maxHeight: '400px',
              borderRadius: '4px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
            }}
          />
          <div style={{
            marginTop: '8px',
            fontSize: '12px',
            color: '#6b7280'
          }}>
            {filename}
          </div>
        </div>
      </div>
    );
  }

  // Regular text observation
  return (
    <pre className="observation-content">
      {formatObservationContent(content)}
    </pre>
  );
};

export const FileWriteActionArgs = ({ args }: { args: any }) => {
  let parsedArgs = args;

  if (typeof args === 'string') {
    try {
      parsedArgs = JSON.parse(args);
    } catch {
      return <pre className="action-args">{args}</pre>;
    }
  }

  const filePath = parsedArgs.file_path || parsedArgs.path || parsedArgs.filename;
  const content = parsedArgs.content || parsedArgs.data;

  if (!filePath || !content) {
    return <pre className="action-args">{JSON.stringify(parsedArgs, null, 2)}</pre>;
  }

  const ext = getFileExtension(filePath);

  if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp'].includes(ext)) {
    return (
      <div className="action-args">
        <div style={{ marginBottom: '8px', fontWeight: 600 }}>
          Writing image: {filePath}
        </div>
        <div style={{ color: '#6b7280', fontSize: '12px' }}>
          (Image preview not available for base64 content)
        </div>
      </div>
    );
  }

  if (['md', 'markdown'].includes(ext)) {
    return (
      <div className="action-args">
        <div style={{ marginBottom: '8px', fontWeight: 600 }}>
          Writing markdown: {filePath}
        </div>
        <div style={{
          background: '#f9fafb',
          border: '1px solid #e5e7eb',
          borderRadius: '6px',
          padding: '12px',
          marginTop: '8px'
        }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code: CodeBlock }}>
            {content}
          </ReactMarkdown>
        </div>
      </div>
    );
  }

  const language = getLanguageFromExtension(ext);

  return (
    <div className="action-args">
      <div style={{ marginBottom: '8px', fontWeight: 600 }}>
        Writing file: {filePath}
      </div>
      <SyntaxHighlighter
        language={language}
        style={oneLight}
        customStyle={{
          margin: '8px 0 0 0',
          borderRadius: '6px',
          border: '1px solid #e5e7eb',
          fontSize: '13px',
        }}
      >
        {content}
      </SyntaxHighlighter>
    </div>
  );
};
