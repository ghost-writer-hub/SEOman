'use client';

import type { ContentBrief } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatRelativeTime, formatNumber } from '@/lib/utils';

interface BriefCardProps {
  brief: ContentBrief;
  onClick?: () => void;
  onGenerate?: () => void;
  onCreateDraft?: () => void;
}

export function BriefCard({ brief, onClick, onGenerate, onCreateDraft }: BriefCardProps) {
  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'ready': return 'success';
      case 'published': return 'info';
      case 'failed': return 'error';
      case 'draft':
      case 'review': return 'warning';
      default: return 'default';
    }
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="cursor-pointer" onClick={onClick}>
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="truncate">{brief.target_keyword}</CardTitle>
            <CardDescription className="mt-1">
              {formatRelativeTime(brief.created_at)}
            </CardDescription>
          </div>
          <Badge variant={getStatusVariant(brief.status)} className="capitalize">
            {brief.status}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        {brief.status === 'ready' && (
          <>
            {brief.title_suggestions && brief.title_suggestions.length > 0 && (
              <div className="mb-3">
                <p className="text-xs text-gray-500 mb-1">Suggested Title</p>
                <p className="text-sm font-medium text-gray-900 line-clamp-2">
                  {brief.title_suggestions[0]}
                </p>
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-gray-500">Target Words</p>
                <p className="font-medium">{formatNumber(brief.target_word_count)}</p>
              </div>
              <div>
                <p className="text-gray-500">Keywords</p>
                <p className="font-medium">{brief.keywords_to_include?.length || 0}</p>
              </div>
            </div>
            
            {brief.content_outline && brief.content_outline.length > 0 && (
              <div className="mt-3">
                <p className="text-xs text-gray-500 mb-1">Outline ({brief.content_outline.length} sections)</p>
                <ul className="space-y-1">
                  {brief.content_outline.slice(0, 3).map((section, i) => (
                    <li key={i} className="text-sm text-gray-700 truncate">
                      • {section.heading}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
        
        {brief.status === 'pending' && (
          <div className="text-center py-4 text-gray-500">
            Brief not generated yet
          </div>
        )}
        
        {brief.status === 'failed' && brief.error_message && (
          <p className="text-sm text-red-600">{brief.error_message}</p>
        )}
      </CardContent>
      
      <CardFooter className="gap-2">
        {brief.status === 'pending' && (
          <Button variant="primary" size="sm" onClick={onGenerate}>
            Generate Brief
          </Button>
        )}
        {brief.status === 'ready' && (
          <Button variant="primary" size="sm" onClick={onCreateDraft}>
            Create Draft
          </Button>
        )}
        <Button variant="outline" size="sm" onClick={onClick}>
          View Details
        </Button>
      </CardFooter>
    </Card>
  );
}
