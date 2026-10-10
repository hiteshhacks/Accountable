import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Renders the GST report Markdown string from /gst/analyze.
 * Raw HTML is not rendered (react-markdown default) and links are shown as plain text,
 * because report content can include untrusted spreadsheet text.
 */
export function MarkdownReport({ markdown }: { markdown: string }) {
  return (
    <div className="ws-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ children }) => (
            <div className="ws-md-table">
              <table>{children}</table>
            </div>
          ),
          a: ({ children }) => <span>{children}</span>,
          img: () => null,
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
