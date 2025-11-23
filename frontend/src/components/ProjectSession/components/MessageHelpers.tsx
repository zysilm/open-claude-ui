import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Process message content to render embedded SVGs and data URIs as actual images
 */
export const processContentWithImages = (content: string): React.ReactNode[] => {
  const elements: React.ReactNode[] = [];
  let lastIndex = 0;
  let keyCounter = 0;

  // Pattern 1: Detect SVG code blocks
  const svgPattern = /<svg\s[^>]*>[\s\S]*?<\/svg>/gi;

  // Pattern 2: Detect data URI images (data:image/...)
  const dataUriPattern = /data:image\/[a-zA-Z]+;base64,[A-Za-z0-9+/=]+/g;

  // Combine both patterns
  const combinedPattern = new RegExp(
    `(${svgPattern.source})|(${dataUriPattern.source})`,
    'gi'
  );

  let match;
  while ((match = combinedPattern.exec(content)) !== null) {
    // Add text before this match
    if (match.index > lastIndex) {
      const textBefore = content.substring(lastIndex, match.index);
      elements.push(
        <span key={`text-${keyCounter++}`}>{textBefore}</span>
      );
    }

    const matchedContent = match[0];

    // Check if it's SVG
    if (matchedContent.startsWith('<svg')) {
      elements.push(
        <div
          key={`svg-${keyCounter++}`}
          style={{
            display: 'inline-block',
            margin: '12px 0',
            padding: '12px',
            background: '#f9fafb',
            border: '1px solid #e5e7eb',
            borderRadius: '6px',
            maxWidth: '100%',
          }}
          dangerouslySetInnerHTML={{ __html: matchedContent }}
        />
      );
    }
    // Check if it's data URI
    else if (matchedContent.startsWith('data:image/')) {
      // Extract mime type for display
      const mimeMatch = matchedContent.match(/data:image\/([a-zA-Z]+);/);
      const imageType = mimeMatch ? mimeMatch[1].toUpperCase() : 'IMAGE';

      elements.push(
        <div
          key={`img-${keyCounter++}`}
          style={{
            margin: '12px 0',
            padding: '12px',
            background: '#f9fafb',
            border: '1px solid #e5e7eb',
            borderRadius: '6px',
            textAlign: 'center',
          }}
        >
          <img
            src={matchedContent}
            alt={`Generated ${imageType}`}
            style={{
              maxWidth: '100%',
              maxHeight: '500px',
              borderRadius: '4px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
            }}
          />
          <div
            style={{
              marginTop: '8px',
              fontSize: '12px',
              color: '#6b7280',
            }}
          >
            {imageType} Image
          </div>
        </div>
      );
    }

    lastIndex = match.index + matchedContent.length;
  }

  // Add remaining text
  if (lastIndex < content.length) {
    elements.push(
      <span key={`text-${keyCounter++}`}>{content.substring(lastIndex)}</span>
    );
  }

  return elements.length > 0 ? elements : [content];
};

/**
 * Component to render message content with embedded images and markdown support
 */
export const MessageContentWithImages: React.FC<{ content: string }> = ({ content }) => {
  const elements: React.ReactNode[] = [];
  let lastIndex = 0;
  let keyCounter = 0;

  // Pattern to detect SVGs and data URIs
  const svgPattern = /<svg\s[^>]*>[\s\S]*?<\/svg>/gi;
  const dataUriPattern = /data:image\/[a-zA-Z]+;base64,[A-Za-z0-9+/=]+/g;
  const combinedPattern = new RegExp(
    `(${svgPattern.source})|(${dataUriPattern.source})`,
    'gi'
  );

  let match;
  while ((match = combinedPattern.exec(content)) !== null) {
    // Add markdown-rendered text before this match
    if (match.index > lastIndex) {
      const textBefore = content.substring(lastIndex, match.index);
      elements.push(
        <ReactMarkdown
          key={`markdown-${keyCounter++}`}
          remarkPlugins={[remarkGfm]}
          components={{ code: CodeBlock }}
        >
          {textBefore}
        </ReactMarkdown>
      );
    }

    const matchedContent = match[0];

    // Render SVG
    if (matchedContent.startsWith('<svg')) {
      elements.push(
        <div
          key={`svg-${keyCounter++}`}
          style={{
            display: 'inline-block',
            margin: '12px 0',
            padding: '12px',
            background: '#f9fafb',
            border: '1px solid #e5e7eb',
            borderRadius: '6px',
            maxWidth: '100%',
          }}
          dangerouslySetInnerHTML={{ __html: matchedContent }}
        />
      );
    }
    // Render data URI image
    else if (matchedContent.startsWith('data:image/')) {
      const mimeMatch = matchedContent.match(/data:image\/([a-zA-Z]+);/);
      const imageType = mimeMatch ? mimeMatch[1].toUpperCase() : 'IMAGE';

      elements.push(
        <div
          key={`img-${keyCounter++}`}
          style={{
            margin: '12px 0',
            padding: '12px',
            background: '#f9fafb',
            border: '1px solid #e5e7eb',
            borderRadius: '6px',
            textAlign: 'center',
          }}
        >
          <img
            src={matchedContent}
            alt={`Generated ${imageType}`}
            style={{
              maxWidth: '100%',
              maxHeight: '500px',
              borderRadius: '4px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
            }}
          />
          <div
            style={{
              marginTop: '8px',
              fontSize: '12px',
              color: '#6b7280',
            }}
          >
            {imageType} Image
          </div>
        </div>
      );
    }

    lastIndex = match.index + matchedContent.length;
  }

  // Add remaining markdown-rendered text
  if (lastIndex < content.length) {
    elements.push(
      <ReactMarkdown
        key={`markdown-${keyCounter++}`}
        remarkPlugins={[remarkGfm]}
        components={{ code: CodeBlock }}
      >
        {content.substring(lastIndex)}
      </ReactMarkdown>
    );
  }

  // If no images found, just render as markdown
  if (elements.length === 0) {
    return (
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code: CodeBlock }}>
        {content}
      </ReactMarkdown>
    );
  }

  return <div className="message-content-with-images">{elements}</div>;
};

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
