'use client';

import { useState, useEffect } from 'react';
import type { ContentDraft } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { formatNumber } from '@/lib/utils';

interface DraftEditorProps {
  draft: ContentDraft;
  targetWordCount?: number;
  onSave: (content: string) => Promise<void>;
  isSaving?: boolean;
}

export function DraftEditor({ draft, targetWordCount = 1500, onSave, isSaving }: DraftEditorProps) {
  const [content, setContent] = useState(draft.content || '');
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    setContent(draft.content || '');
    setIsDirty(false);
  }, [draft.id, draft.content]);

  const wordCount = content.trim().split(/\s+/).filter(Boolean).length;
  const progress = Math.min(100, (wordCount / targetWordCount) * 100);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    setIsDirty(true);
  };

  const handleSave = async () => {
    await onSave(content);
    setIsDirty(false);
  };

  const getScoreColor = (score?: number) => {
    if (!score) return 'default';
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-4">
          <Badge variant={getScoreColor(draft.seo_score)}>
            SEO Score: {draft.seo_score || '-'}
          </Badge>
          <span className="text-sm text-gray-600">
            Version {draft.version}
          </span>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-600">
            <span className="font-medium">{formatNumber(wordCount)}</span>
            <span className="text-gray-400"> / {formatNumber(targetWordCount)} words</span>
          </div>
          
          <Button
            onClick={handleSave}
            disabled={!isDirty}
            isLoading={isSaving}
          >
            {isDirty ? 'Save Changes' : 'Saved'}
          </Button>
        </div>
      </div>
      
      {/* Progress bar */}
      <div className="px-4 pt-2">
        <Progress value={progress} size="sm" variant={progress >= 100 ? 'success' : 'default'} />
      </div>
      
      {/* Editor */}
      <div className="flex-1 p-4">
        <textarea
          value={content}
          onChange={handleChange}
          className="w-full h-full p-4 border border-gray-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
          placeholder="Start writing your content here...

Use Markdown formatting:
# Heading 1
## Heading 2
**bold text**
*italic text*
- bullet points
1. numbered lists"
        />
      </div>
      
      {/* Status bar */}
      <div className="flex items-center justify-between px-4 py-2 border-t border-gray-200 bg-gray-50 text-xs text-gray-500">
        <span>Draft status: {draft.status}</span>
        <span>
          {isDirty && <span className="text-yellow-600 mr-2">Unsaved changes</span>}
          Press Ctrl+S to save
        </span>
      </div>
    </div>
  );
}
