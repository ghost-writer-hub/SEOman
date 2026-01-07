'use client';

import type { AuditRun } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { formatRelativeTime, getStatusColor, getScoreColor } from '@/lib/utils';

interface AuditCardProps {
  audit: AuditRun;
  siteName?: string;
  onClick?: () => void;
}

export function AuditCard({ audit, siteName, onClick }: AuditCardProps) {
  const getScoreVariant = (score: number | undefined) => {
    if (!score) return 'default';
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  return (
    <Card 
      className="hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-base">
              {siteName || `Audit ${audit.id.slice(0, 8)}`}
            </CardTitle>
            <p className="text-sm text-gray-500 mt-1">
              {formatRelativeTime(audit.created_at)}
            </p>
          </div>
          <Badge className={getStatusColor(audit.status)}>
            {audit.status}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        {audit.status === 'completed' && (
          <>
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-gray-600">Score</span>
              <span className={`text-2xl font-bold ${getScoreColor(audit.score)}`}>
                {audit.score ?? '-'}
              </span>
            </div>
            
            <Progress 
              value={audit.score || 0} 
              variant={getScoreVariant(audit.score)}
              size="sm"
            />
            
            <div className="grid grid-cols-4 gap-2 mt-4 text-center">
              <div>
                <p className="text-lg font-semibold text-red-600">{audit.critical_count}</p>
                <p className="text-xs text-gray-500">Critical</p>
              </div>
              <div>
                <p className="text-lg font-semibold text-orange-600">{audit.high_count}</p>
                <p className="text-xs text-gray-500">High</p>
              </div>
              <div>
                <p className="text-lg font-semibold text-yellow-600">{audit.medium_count}</p>
                <p className="text-xs text-gray-500">Medium</p>
              </div>
              <div>
                <p className="text-lg font-semibold text-blue-600">{audit.low_count}</p>
                <p className="text-xs text-gray-500">Low</p>
              </div>
            </div>
          </>
        )}
        
        {audit.status === 'running' && (
          <div className="flex items-center justify-center py-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            <span className="ml-3 text-gray-600">Analyzing...</span>
          </div>
        )}
        
        {audit.status === 'failed' && audit.error_message && (
          <p className="text-sm text-red-600 mt-2">{audit.error_message}</p>
        )}
      </CardContent>
    </Card>
  );
}
