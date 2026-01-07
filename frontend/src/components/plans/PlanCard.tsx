'use client';

import type { SeoPlan } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { Button } from '@/components/ui/Button';
import { formatDate, getStatusColor } from '@/lib/utils';

interface PlanCardProps {
  plan: SeoPlan;
  onClick?: () => void;
  onEdit?: () => void;
}

export function PlanCard({ plan, onClick, onEdit }: PlanCardProps) {
  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'completed': return 'info';
      case 'archived': return 'default';
      default: return 'warning';
    }
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="cursor-pointer" onClick={onClick}>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>{plan.title}</CardTitle>
            {plan.description && (
              <CardDescription className="mt-1 line-clamp-2">
                {plan.description}
              </CardDescription>
            )}
          </div>
          <Badge variant={getStatusVariant(plan.status)} className="capitalize">
            {plan.status}
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="mb-4">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">Progress</span>
            <span className="font-medium">{plan.progress_percent}%</span>
          </div>
          <Progress value={plan.progress_percent} size="md" />
        </div>
        
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500">Start Date</p>
            <p className="font-medium">{formatDate(plan.start_date) || 'Not set'}</p>
          </div>
          <div>
            <p className="text-gray-500">End Date</p>
            <p className="font-medium">{formatDate(plan.end_date) || 'Not set'}</p>
          </div>
        </div>
        
        {plan.goals && plan.goals.length > 0 && (
          <div className="mt-4">
            <p className="text-sm text-gray-500 mb-2">Goals</p>
            <ul className="space-y-1">
              {plan.goals.slice(0, 3).map((goal, index) => (
                <li key={index} className="text-sm text-gray-700 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                  {goal}
                </li>
              ))}
              {plan.goals.length > 3 && (
                <li className="text-sm text-gray-500">
                  +{plan.goals.length - 3} more goals
                </li>
              )}
            </ul>
          </div>
        )}
      </CardContent>
      
      <CardFooter className="gap-2">
        <Button variant="primary" size="sm" onClick={onClick}>
          View Details
        </Button>
        <Button variant="outline" size="sm" onClick={onEdit}>
          Edit
        </Button>
      </CardFooter>
    </Card>
  );
}
