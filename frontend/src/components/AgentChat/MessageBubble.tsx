/**
 * Message Bubble Component for Agent Chat
 *
 * Displays individual messages in the agent chat interface with different
 * styling for user vs agent messages. Supports basic markdown formatting
 * and copy functionality for code blocks.
 */

import React, { useState } from "react";
import { Copy, Check } from "lucide-react";
import toast from "react-hot-toast";

interface Message {
  role: "user" | "agent";
  content: string;
  timestamp: string;
}

interface MessageBubbleProps {
  message: Message;
}

/**
 * Parse markdown in message content for bold and italic text
 * Supports: **bold**, __bold__, *italic*, _italic_
 */
function parseMarkdown(text: string): (string | JSX.Element)[] {
  const parts: (string | JSX.Element)[] = [];
  let lastIndex = 0;

  // Bold pattern: **text** or __text__
  const boldRegex = /\*\*([^\*]+)\*\*|__([^_]+)__/g;
  // Italic pattern: *text* or _text_ (but not inside bold)
  const italicRegex = /(?<!\*)\*([^\*\n]+)\*(?!\*)|(?<!_)_([^_\n]+)_(?!_)/g;
  // Code pattern: `code`
  const codeRegex = /`([^`]+)`/g;

  // Simple approach: replace patterns with JSX elements
  let result = text;

  // Replace bold
  result = result.replace(/\*\*([^\*]+)\*\*|__([^_]+)__/g, (match, p1, p2) => {
    const content = p1 || p2;
    return `<bold>${content}</bold>`;
  });

  // Replace italic (avoid already-bolded content)
  result = result.replace(/\*([^\*\n]+)\*|_([^_\n]+)_/g, (match, p1, p2) => {
    const content = p1 || p2;
    if (!content.includes("<bold>")) {
      return `<italic>${content}</italic>`;
    }
    return match;
  });

  // Replace code
  result = result.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Parse result into JSX elements
  const parser = new DOMParser();
  const doc = parser.parseFromString(
    `<root>${result.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</root>`,
    "text/xml"
  );

  // Actually, let's use a simpler regex-based approach
  let index = 0;
  const boldPattern = /\*\*([^\*]+)\*\*|__([^_]+)__/g;
  let match;

  // Process bold
  const boldMatches: Array<{ pattern: RegExp; key: string; replace: (m: string, p1: string, p2: string) => JSX.Element }> = [];

  // Split by bold, italic, and code patterns
  let processedText = text;
  const elements: (string | JSX.Element)[] = [];

  // Handle bold
  processedText = text.replace(/\*\*([^\*]+)\*\*|__([^_]+)__/g, (match, p1, p2) => {
    const content = p1 || p2;
    return `<BOLD>${content}</BOLD>`;
  });

  // Handle italic (but not inside bold)
  processedText = processedText.replace(
    /(?<!<BOLD>)\*([^\*\n]+)\*(?!<\/BOLD>)|(?<!<BOLD>)_([^_\n]+)_(?!<\/BOLD>)/g,
    (match, p1, p2) => {
      return `<ITALIC>${p1 || p2}</ITALIC>`;
    }
  );

  // Handle code
  processedText = processedText.replace(/`([^`]+)`/g, "<CODE>$1</CODE>");

  // Split and create JSX elements
  const parts2 = processedText.split(/(<BOLD>[^<]+<\/BOLD>|<ITALIC>[^<]+<\/ITALIC>|<CODE>[^<]+<\/CODE>)/);

  return parts2.map((part, idx) => {
    if (part.startsWith("<BOLD>")) {
      const content = part.replace(/<BOLD>|<\/BOLD>/g, "");
      return (
        <strong key={idx} className="font-bold">
          {content}
        </strong>
      );
    }
    if (part.startsWith("<ITALIC>")) {
      const content = part.replace(/<ITALIC>|<\/ITALIC>/g, "");
      return (
        <em key={idx} className="italic">
          {content}
        </em>
      );
    }
    if (part.startsWith("<CODE>")) {
      const content = part.replace(/<CODE>|<\/CODE>/g, "");
      return (
        <code
          key={idx}
          className="bg-gray-800 text-yellow-300 px-2 py-1 rounded text-sm font-mono"
        >
          {content}
        </code>
      );
    }
    return part;
  });
}

/**
 * Format timestamp to human-readable format
 */
function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Ahora";
    if (diffMins < 60) return `Hace ${diffMins}m`;
    if (diffHours < 24) return `Hace ${diffHours}h`;
    if (diffDays < 7) return `Hace ${diffDays}d`;

    return date.toLocaleDateString("es-EC", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return new Date(timestamp).toLocaleTimeString("es-EC");
  }
}

/**
 * Check if message contains code blocks
 */
function hasCodeBlock(content: string): boolean {
  return /`[^`]+`/.test(content);
}

/**
 * Message Bubble Component
 *
 * Features:
 * - Different styling for user vs agent messages
 * - User messages: right-aligned, blue background
 * - Agent messages: left-aligned, gray background
 * - Markdown support (bold, italic, code)
 * - Copy button for code blocks
 * - Timestamp display with smart formatting
 * - Proper spacing and typography
 */
export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const [copied, setCopied] = useState(false);

  const isUser = message.role === "user";
  const hasCode = hasCodeBlock(message.content);
  const parsedContent = parseMarkdown(message.content);

  /**
   * Handle copy code to clipboard
   */
  const handleCopy = () => {
    const codeContent = message.content
      .replace(/`([^`]+)`/g, "$1")
      .match(/`[^`]+`/)?.[0]
      ?.replace(/`/g, "");

    if (codeContent) {
      navigator.clipboard.writeText(codeContent);
      setCopied(true);
      toast.success("Código copiado");
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      className={`flex gap-3 mb-4 animate-in fade-in slide-in-from-bottom-2 duration-300 ${
        isUser ? "flex-row-reverse" : "flex-row"
      }`}
    >
      {/* Avatar */}
      <div
        className={`
          flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
          ${isUser ? "bg-blue-600" : "bg-gray-600"}
        `}
      >
        <span className="text-white text-sm font-bold">
          {isUser ? "👤" : "🤖"}
        </span>
      </div>

      {/* Message Content */}
      <div className={`flex flex-col gap-1 max-w-xs ${isUser ? "items-end" : "items-start"}`}>
        {/* Bubble */}
        <div
          className={`
            px-4 py-2 rounded-lg break-words
            ${
              isUser
                ? "bg-blue-600 text-white rounded-br-none"
                : "bg-gray-700 text-gray-100 rounded-bl-none"
            }
          `}
        >
          {/* Render parsed markdown content */}
          <div className="text-sm space-y-1">
            {typeof parsedContent === "string" ? (
              <span>{parsedContent}</span>
            ) : (
              <span>{parsedContent}</span>
            )}
          </div>

          {/* Copy Button for Code Blocks */}
          {hasCode && !isUser && (
            <button
              onClick={handleCopy}
              className="mt-2 inline-flex items-center gap-1 text-xs bg-gray-800 hover:bg-gray-900 text-yellow-300 px-2 py-1 rounded transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3" />
                  Copiado
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  Copiar
                </>
              )}
            </button>
          )}
        </div>

        {/* Timestamp */}
        <span className="text-xs text-gray-500 px-2">
          {formatTimestamp(message.timestamp)}
        </span>
      </div>
    </div>
  );
};

export default MessageBubble;

