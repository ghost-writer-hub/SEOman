'use client';

import type { Keyword } from '@/lib/types';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatNumber, formatCurrency } from '@/lib/utils';

interface KeywordTableProps {
  keywords: Keyword[];
  onTrack?: (id: string, track: boolean) => void;
}

export function KeywordTable({ keywords, onTrack }: KeywordTableProps) {
  const getPositionChange = (current?: number, previous?: number) => {
    if (!current || !previous) return null;
    const change = previous - current;
    if (change > 0) return { value: change, direction: 'up' as const };
    if (change < 0) return { value: Math.abs(change), direction: 'down' as const };
    return { value: 0, direction: 'same' as const };
  };

  const getIntentColor = (intent?: string) => {
    switch (intent?.toLowerCase()) {
      case 'transactional': return 'success';
      case 'commercial': return 'info';
      case 'informational': return 'warning';
      case 'navigational': return 'default';
      default: return 'default';
    }
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Keyword</TableHead>
          <TableHead className="text-right">Volume</TableHead>
          <TableHead className="text-right">CPC</TableHead>
          <TableHead className="text-right">Difficulty</TableHead>
          <TableHead>Intent</TableHead>
          <TableHead className="text-right">Position</TableHead>
          <TableHead className="text-center">Tracked</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {keywords.map((keyword) => {
          const change = getPositionChange(keyword.current_position, keyword.previous_position);
          
          return (
            <TableRow key={keyword.id}>
              <TableCell className="font-medium">{keyword.keyword}</TableCell>
              <TableCell className="text-right">
                {formatNumber(keyword.search_volume)}
              </TableCell>
              <TableCell className="text-right">
                {keyword.cpc ? formatCurrency(keyword.cpc) : '-'}
              </TableCell>
              <TableCell className="text-right">
                {keyword.difficulty !== undefined ? (
                  <span className={
                    keyword.difficulty >= 70 ? 'text-red-600' :
                    keyword.difficulty >= 40 ? 'text-yellow-600' :
                    'text-green-600'
                  }>
                    {keyword.difficulty}
                  </span>
                ) : '-'}
              </TableCell>
              <TableCell>
                {keyword.intent && (
                  <Badge variant={getIntentColor(keyword.intent)} className="capitalize">
                    {keyword.intent}
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex items-center justify-end gap-1">
                  <span>{keyword.current_position || '-'}</span>
                  {change && change.direction !== 'same' && (
                    <span className={
                      change.direction === 'up' ? 'text-green-600' : 'text-red-600'
                    }>
                      {change.direction === 'up' ? '↑' : '↓'}
                      {change.value}
                    </span>
                  )}
                </div>
              </TableCell>
              <TableCell className="text-center">
                <Button
                  variant={keyword.is_tracked ? 'primary' : 'outline'}
                  size="sm"
                  onClick={() => onTrack?.(keyword.id, !keyword.is_tracked)}
                >
                  {keyword.is_tracked ? 'Tracking' : 'Track'}
                </Button>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
