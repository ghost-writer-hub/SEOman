'use client';

import type { Site } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatRelativeTime, extractDomain } from '@/lib/utils';

interface SiteCardProps {
  site: Site;
  onEdit?: (site: Site) => void;
  onDelete?: (site: Site) => void;
  onAudit?: (site: Site) => void;
}

export function SiteCard({ site, onEdit, onDelete, onAudit }: SiteCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg">{site.name}</CardTitle>
            <CardDescription className="mt-1">
              {extractDomain(site.url)}
            </CardDescription>
          </div>
          <Badge variant={site.is_active ? 'success' : 'default'}>
            {site.is_active ? 'Active' : 'Inactive'}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500">Last Audit</p>
            <p className="font-medium text-gray-900">
              {site.last_audit_at ? formatRelativeTime(site.last_audit_at) : 'Never'}
            </p>
          </div>
          <div>
            <p className="text-gray-500">Schedule</p>
            <p className="font-medium text-gray-900 capitalize">
              {site.audit_schedule || 'Manual'}
            </p>
          </div>
        </div>
        
        {site.description && (
          <p className="mt-4 text-sm text-gray-600 line-clamp-2">
            {site.description}
          </p>
        )}
      </CardContent>
      
      <CardFooter className="gap-2">
        <Button variant="primary" size="sm" onClick={() => onAudit?.(site)}>
          Run Audit
        </Button>
        <Button variant="outline" size="sm" onClick={() => onEdit?.(site)}>
          Edit
        </Button>
        <Button variant="ghost" size="sm" className="text-red-600 hover:bg-red-50" onClick={() => onDelete?.(site)}>
          Delete
        </Button>
      </CardFooter>
    </Card>
  );
}
