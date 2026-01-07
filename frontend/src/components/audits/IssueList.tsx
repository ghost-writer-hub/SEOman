'use client';

import type { SeoIssue } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { getSeverityColor, truncate } from '@/lib/utils';

interface IssueListProps {
  issues: SeoIssue[];
  onMarkFixed?: (issueId: string) => void;
}

export function IssueList({ issues, onMarkFixed }: IssueListProps) {
  const getSeverityVariant = (severity: string) => {
    switch (severity) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  if (issues.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No issues found. Great job!
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {issues.map((issue) => (
        <div
          key={issue.id}
          className={`p-4 rounded-lg border ${issue.is_fixed ? 'bg-green-50 border-green-200' : 'bg-white border-gray-200'}`}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Badge variant={getSeverityVariant(issue.severity)} className="capitalize">
                  {issue.severity}
                </Badge>
                <span className="text-xs text-gray-500 capitalize">{issue.category}</span>
                {issue.is_fixed && (
                  <Badge variant="success">Fixed</Badge>
                )}
              </div>
              
              <h4 className="font-medium text-gray-900">{issue.title}</h4>
              
              {issue.description && (
                <p className="text-sm text-gray-600 mt-1">
                  {truncate(issue.description, 150)}
                </p>
              )}
              
              {issue.affected_url && (
                <p className="text-xs text-blue-600 mt-2 truncate">
                  {issue.affected_url}
                </p>
              )}
              
              {issue.recommendation && (
                <div className="mt-2 p-2 bg-gray-50 rounded text-sm text-gray-700">
                  <strong>Recommendation:</strong> {issue.recommendation}
                </div>
              )}
            </div>
            
            {!issue.is_fixed && onMarkFixed && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onMarkFixed(issue.id)}
              >
                Mark Fixed
              </Button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
