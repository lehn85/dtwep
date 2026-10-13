import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Save, RotateCcw, FileText, Check, AlertCircle, Copy, CheckCircle2 } from 'lucide-react';
import yaml from 'js-yaml';
import { ConfigInfo } from '../types';

interface ConfigEditorProps {
  configInfo: ConfigInfo | null;
  onSave: (yamlContent: string) => Promise<void>;
  isSaving: boolean;
}

// Helper to find unquoted comment start in a YAML line
function findUnquotedCommentIndex(line: string): number {
  let inSingle = false;
  let inDouble = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === "'" && !inDouble) {
      inSingle = !inSingle;
    } else if (ch === '"' && !inSingle && (i === 0 || line[i - 1] !== '\\')) {
      inDouble = !inDouble;
    } else if (ch === '#' && !inSingle && !inDouble) {
      if (i === 0 || /\s/.test(line[i - 1])) {
        return i;
      }
    }
  }
  return -1;
}

// Tokenize value portion of a YAML line
function tokenizeValue(valueStr: string): Array<{ text: string; className: string }> {
  const tokens: Array<{ text: string; className: string }> = [];
  const regex = /("(?:\\.|[^"\\])*"|'[^']*'|\[|\]|\{|\}|,|true|false|TRUE|FALSE|True|False|null|NULL|Null|yes|no|YES|NO|~|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|[^\s"'{}[\]:,]+|\s+)/g;
  let match;
  while ((match = regex.exec(valueStr)) !== null) {
    const text = match[0];
    if (/^"(?:\\.|[^"\\])*"$|^'[^']*'$/.test(text)) {
      tokens.push({ text, className: 'text-emerald-400 dark:text-emerald-300' });
    } else if (/^(true|false|TRUE|FALSE|True|False|yes|no|YES|NO)$/.test(text)) {
      tokens.push({ text, className: 'text-rose-400 font-semibold' });
    } else if (/^(null|NULL|Null|~)$/.test(text)) {
      tokens.push({ text, className: 'text-pink-400 font-semibold' });
    } else if (/^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(text)) {
      tokens.push({ text, className: 'text-amber-400 dark:text-amber-300' });
    } else if (/^[\[\]\{\},]$/.test(text)) {
      tokens.push({ text, className: 'text-purple-400 font-bold' });
    } else if (/^[|>][\-+]?$/.test(text)) {
      tokens.push({ text, className: 'text-indigo-400 font-bold' });
    } else if (/^\s+$/.test(text)) {
      tokens.push({ text, className: '' });
    } else {
      tokens.push({ text, className: 'text-slate-200 dark:text-slate-100' });
    }
  }
  if (tokens.length === 0 && valueStr.length > 0) {
    tokens.push({ text: valueStr, className: 'text-slate-200 dark:text-slate-100' });
  }
  return tokens;
}

// Tokenize a single YAML line
function tokenizeYamlLine(line: string): Array<{ text: string; className: string }> {
  if (/^\s*#/.test(line)) {
    return [{ text: line, className: 'text-slate-500 dark:text-slate-500 italic' }];
  }
  if (/^---|\.\.\./.test(line.trim())) {
    return [{ text: line, className: 'text-purple-400 font-bold' }];
  }

  let comment = '';
  let content = line;
  const commentIdx = findUnquotedCommentIndex(line);
  if (commentIdx !== -1) {
    content = line.substring(0, commentIdx);
    comment = line.substring(commentIdx);
  }

  const tokens: Array<{ text: string; className: string }> = [];

  const kvMatch = content.match(/^(\s*(?:-\s+)?)(['"]?[a-zA-Z0-9_\-\.\/ ]+?['"]?)(\s*:\s*)(.*)$/);
  if (kvMatch) {
    const [, indentPrefix, keyPart, colonPart, valPart] = kvMatch;
    if (indentPrefix) {
      if (indentPrefix.includes('-')) {
        const parts = indentPrefix.split('-');
        tokens.push({ text: parts[0], className: 'text-slate-400' });
        tokens.push({ text: '-', className: 'text-cyan-400 font-bold' });
        tokens.push({ text: parts.slice(1).join('-'), className: 'text-slate-400' });
      } else {
        tokens.push({ text: indentPrefix, className: 'text-slate-400' });
      }
    }
    tokens.push({ text: keyPart, className: 'text-sky-400 dark:text-sky-300 font-medium' });
    tokens.push({ text: colonPart, className: 'text-slate-400 font-bold' });
    if (valPart) {
      tokens.push(...tokenizeValue(valPart));
    }
  } else {
    const listMatch = content.match(/^(\s*-\s+)(.*)$/);
    if (listMatch) {
      const [, prefix, rest] = listMatch;
      const parts = prefix.split('-');
      tokens.push({ text: parts[0], className: 'text-slate-400' });
      tokens.push({ text: '-', className: 'text-cyan-400 font-bold' });
      tokens.push({ text: parts.slice(1).join('-'), className: 'text-slate-400' });
      tokens.push(...tokenizeValue(rest));
    } else {
      tokens.push(...tokenizeValue(content));
    }
  }

  if (comment) {
    tokens.push({ text: comment, className: 'text-slate-500 dark:text-slate-500 italic' });
  }

  return tokens;
}

export const ConfigEditor: React.FC<ConfigEditorProps> = ({
  configInfo,
  onSave,
  isSaving,
}) => {
  const [rawYaml, setRawYaml] = useState<string>('');
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [errorLineNumber, setErrorLineNumber] = useState<number | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [cursorPos, setCursorPos] = useState<{ line: number; col: number }>({ line: 1, col: 1 });

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const preRef = useRef<HTMLPreElement>(null);
  const gutterRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (configInfo?.raw_yaml) {
      setRawYaml(configInfo.raw_yaml);
      validateYaml(configInfo.raw_yaml);
    }
  }, [configInfo]);

  const validateYaml = (content: string) => {
    try {
      yaml.load(content);
      setYamlError(null);
      setErrorLineNumber(null);
      return true;
    } catch (err: any) {
      setYamlError(err.message || 'Invalid YAML format');
      if (err.mark && typeof err.mark.line === 'number') {
        setErrorLineNumber(err.mark.line + 1);
      } else {
        setErrorLineNumber(null);
      }
      return false;
    }
  };

  const handleYamlChange = (newYaml: string) => {
    setRawYaml(newYaml);
    setSaveSuccess(false);
    validateYaml(newYaml);
  };

  const handleScroll = () => {
    if (!textareaRef.current) return;
    const { scrollTop, scrollLeft } = textareaRef.current;
    if (preRef.current) {
      preRef.current.scrollTop = scrollTop;
      preRef.current.scrollLeft = scrollLeft;
    }
    if (gutterRef.current) {
      gutterRef.current.scrollTop = scrollTop;
    }
  };

  const updateCursorPosition = (textarea: HTMLTextAreaElement) => {
    const pos = textarea.selectionStart;
    const lines = textarea.value.substring(0, pos).split('\n');
    const line = lines.length;
    const col = lines[lines.length - 1].length + 1;
    setCursorPos({ line, col });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const textarea = e.currentTarget;
    const { selectionStart, selectionEnd, value } = textarea;

    if (e.key === 'Tab') {
      e.preventDefault();
      if (e.shiftKey) {
        // Shift+Tab: Unindent 2 spaces
        const beforeCursor = value.substring(0, selectionStart);
        const afterCursor = value.substring(selectionEnd);
        const currentLineStart = beforeCursor.lastIndexOf('\n') + 1;
        const currentLine = beforeCursor.substring(currentLineStart);
        if (currentLine.startsWith('  ')) {
          const newValue = value.substring(0, currentLineStart) + currentLine.substring(2) + afterCursor;
          handleYamlChange(newValue);
          setTimeout(() => {
            textarea.selectionStart = Math.max(currentLineStart, selectionStart - 2);
            textarea.selectionEnd = Math.max(currentLineStart, selectionEnd - 2);
          }, 0);
        }
      } else {
        // Tab: Insert 2 spaces
        const newValue = value.substring(0, selectionStart) + '  ' + value.substring(selectionEnd);
        handleYamlChange(newValue);
        setTimeout(() => {
          textarea.selectionStart = selectionStart + 2;
          textarea.selectionEnd = selectionStart + 2;
        }, 0);
      }
    } else if (e.key === 'Enter') {
      // Smart indentation: maintain indentation level
      const beforeCursor = value.substring(0, selectionStart);
      const lastNewline = beforeCursor.lastIndexOf('\n');
      const currentLine = lastNewline === -1 ? beforeCursor : beforeCursor.substring(lastNewline + 1);
      const indentMatch = currentLine.match(/^(\s*)/);
      const indent = indentMatch ? indentMatch[1] : '';
      const extraIndent = /:\s*$/.test(currentLine.trim()) ? '  ' : '';
      const fullIndent = indent + extraIndent;

      if (fullIndent.length > 0) {
        e.preventDefault();
        const afterCursor = value.substring(selectionEnd);
        const insertText = '\n' + fullIndent;
        const newValue = beforeCursor + insertText + afterCursor;
        handleYamlChange(newValue);
        setTimeout(() => {
          textarea.selectionStart = selectionStart + insertText.length;
          textarea.selectionEnd = selectionStart + insertText.length;
        }, 0);
      }
    }
  };

  const handleSaveClick = async () => {
    if (yamlError) return;
    await onSave(rawYaml);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const handleReset = () => {
    if (configInfo?.raw_yaml) {
      handleYamlChange(configInfo.raw_yaml);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(rawYaml);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  // Memoized syntax highlighted lines
  const lines = useMemo(() => {
    return rawYaml.split('\n');
  }, [rawYaml]);

  const highlightedLines = useMemo(() => {
    return lines.map((line, idx) => {
      const tokens = tokenizeYamlLine(line);
      return (
        <div key={idx} className="h-6 leading-6 whitespace-pre">
          {tokens.map((token, tIdx) => (
            <span key={tIdx} className={token.className}>
              {token.text}
            </span>
          ))}
          {/* Ensure empty lines retain height */}
          {tokens.length === 0 && ' '}
        </div>
      );
    });
  }, [lines]);

  if (!configInfo) {
    return (
      <div className="glass-panel rounded-2xl p-6 text-center text-slate-500 dark:text-slate-400 text-sm">
        No configuration selected or available for this experiment.
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-2xl p-5 flex flex-col gap-4 shadow-xl">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-white/5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            <h3 className="font-display font-bold text-base text-slate-900 dark:text-white">
              {configInfo.config_name}
            </h3>
            <span className="text-[11px] font-mono text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-white/5 px-2.5 py-0.5 rounded-md border border-slate-200/80 dark:border-white/5">
              {configInfo.file_path}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            {yamlError ? (
              <span className="inline-flex items-center gap-1 font-mono text-[11px] text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 px-2 py-0.5 rounded border border-rose-200 dark:border-rose-800/40">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Syntax Error {errorLineNumber ? `at line ${errorLineNumber}` : ''}</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 font-mono text-[11px] text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-800/40">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Valid YAML</span>
              </span>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 self-end sm:self-auto">
          {/* Copy Button */}
          <button
            onClick={handleCopy}
            title="Copy YAML content"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 hover:text-slate-900 border border-slate-200/80 dark:bg-white/5 dark:hover:bg-white/10 dark:text-slate-300 dark:hover:text-white dark:border-white/10 text-xs font-medium transition-colors shadow-sm cursor-pointer"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-500" />
                <span className="text-emerald-600 dark:text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>

          {/* Reset Button */}
          <button
            onClick={handleReset}
            title="Reset to initial file contents"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 hover:text-slate-900 border border-slate-200/80 dark:bg-white/5 dark:hover:bg-white/10 dark:text-slate-300 dark:hover:text-white dark:border-white/10 text-xs font-medium transition-colors shadow-sm cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>

          {/* Save Button */}
          <button
            onClick={handleSaveClick}
            disabled={isSaving || !!yamlError}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              saveSuccess
                ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-500/25'
                : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-500/25'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {saveSuccess ? (
              <>
                <Check className="w-3.5 h-3.5" />
                <span>Saved</span>
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                <span>{isSaving ? 'Saving...' : 'Save YAML'}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* YAML Error Alert Banner */}
      {yamlError && (
        <div className="flex items-start gap-2.5 p-3 rounded-xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900/60 text-rose-800 dark:text-rose-300 text-xs font-mono">
          <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-0.5 overflow-x-auto">
            <p className="font-semibold text-rose-700 dark:text-rose-200">YAML Syntax Error:</p>
            <p className="text-[11px] whitespace-pre-wrap leading-relaxed opacity-90">{yamlError}</p>
          </div>
        </div>
      )}

      {/* Syntax Highlighted YAML Text Editor */}
      <div className="relative rounded-xl border border-slate-800 bg-[#090d16] shadow-2xl overflow-hidden flex flex-col font-mono text-xs">
        {/* Editor Toolbar / Header */}
        <div className="flex items-center justify-between px-3 py-1.5 bg-[#0e1322] border-b border-slate-800/80 text-[11px] text-slate-400">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block"></span>
            <span className="ml-2 font-mono text-slate-400">yaml-editor</span>
          </div>
          <div className="flex items-center gap-3 text-slate-400 text-[11px]">
            <span>Tab size: 2</span>
            <span>UTF-8</span>
          </div>
        </div>

        {/* Main Editor Body */}
        <div className="relative flex h-[520px] overflow-hidden">
          {/* Line Numbers Gutter */}
          <div
            ref={gutterRef}
            className="w-12 py-3 bg-[#0c101d] border-r border-slate-800/60 text-slate-600 select-none text-right pr-3 overflow-hidden flex-shrink-0 font-mono text-xs"
          >
            {lines.map((_, idx) => {
              const lineNum = idx + 1;
              const isErrorLine = errorLineNumber === lineNum;
              const isCurrentLine = cursorPos.line === lineNum;
              return (
                <div
                  key={idx}
                  className={`h-6 leading-6 ${
                    isErrorLine
                      ? 'text-rose-500 font-bold bg-rose-500/20 rounded-r'
                      : isCurrentLine
                      ? 'text-purple-300 font-semibold'
                      : 'text-slate-600'
                  }`}
                >
                  {lineNum}
                </div>
              );
            })}
          </div>

          {/* Highlighted Code Container & Overlay Textarea */}
          <div className="relative flex-1 h-full overflow-hidden bg-[#090d16]">
            {/* Syntax Highlighted View Underneath */}
            <pre
              ref={preRef}
              aria-hidden="true"
              className="absolute inset-0 p-3 m-0 overflow-hidden font-mono text-xs leading-6 pointer-events-none select-none whitespace-pre"
              style={{
                tabSize: 2,
              }}
            >
              {highlightedLines}
            </pre>

            {/* Editable Textarea Overlaid on Top */}
            <textarea
              ref={textareaRef}
              value={rawYaml}
              onChange={(e) => {
                handleYamlChange(e.target.value);
                updateCursorPosition(e.target);
              }}
              onScroll={handleScroll}
              onKeyDown={handleKeyDown}
              onClick={(e) => updateCursorPosition(e.currentTarget)}
              onKeyUp={(e) => updateCursorPosition(e.currentTarget)}
              onSelect={(e) => updateCursorPosition(e.currentTarget)}
              rows={22}
              spellCheck={false}
              autoCapitalize="off"
              autoComplete="off"
              autoCorrect="off"
              className="absolute inset-0 w-full h-full p-3 m-0 bg-transparent text-transparent caret-white focus:caret-cyan-400 font-mono text-xs leading-6 outline-none border-none resize-none overflow-auto whitespace-pre selection:bg-purple-500/30 selection:text-transparent"
              style={{
                tabSize: 2,
              }}
            />
          </div>
        </div>

        {/* Editor Status Bar */}
        <div className="flex items-center justify-between px-3 py-1.5 bg-[#0c101d] border-t border-slate-800/80 text-[11px] text-slate-400 font-mono">
          <div className="flex items-center gap-3">
            <span>
              Ln {cursorPos.line}, Col {cursorPos.col}
            </span>
            <span className="text-slate-600">|</span>
            <span>{lines.length} lines</span>
            <span className="text-slate-600">|</span>
            <span>{rawYaml.length} chars</span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-slate-400">YAML</span>
          </div>
        </div>
      </div>
    </div>
  );
};
