'use client';

import type { SeoTask, TaskStatus } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatDate, snakeToTitle } from '@/lib/utils';

interface TaskListProps {
  tasks: SeoTask[];
  onStatusChange?: (taskId: string, status: TaskStatus) => void;
}

export function TaskList({ tasks, onStatusChange }: TaskListProps) {
  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'in_progress': return 'info';
      case 'skipped': return 'default';
      default: return 'warning';
    }
  };

  const getPriorityLabel = (priority: number) => {
    if (priority >= 3) return 'High';
    if (priority === 2) return 'Medium';
    return 'Low';
  };

  const getPriorityColor = (priority: number) => {
    if (priority >= 3) return 'text-red-600';
    if (priority === 2) return 'text-yellow-600';
    return 'text-gray-600';
  };

  if (tasks.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No tasks yet. Add tasks to track your SEO progress.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {tasks.map((task) => (
        <div
          key={task.id}
          className={`p-4 rounded-lg border ${
            task.status === 'completed' ? 'bg-green-50 border-green-200' : 'bg-white border-gray-200'
          }`}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <Badge variant={getStatusVariant(task.status)}>
                  {snakeToTitle(task.status)}
                </Badge>
                <span className={`text-xs font-medium ${getPriorityColor(task.priority)}`}>
                  {getPriorityLabel(task.priority)} Priority
                </span>
                {task.category && (
                  <span className="text-xs text-gray-500 capitalize">{task.category}</span>
                )}
              </div>
              
              <h4 className={`font-medium ${task.status === 'completed' ? 'line-through text-gray-500' : 'text-gray-900'}`}>
                {task.title}
              </h4>
              
              {task.description && (
                <p className="text-sm text-gray-600 mt-1">{task.description}</p>
              )}
              
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                {task.due_date && (
                  <span>Due: {formatDate(task.due_date)}</span>
                )}
                {task.estimated_hours && (
                  <span>{task.estimated_hours}h estimated</span>
                )}
              </div>
            </div>
            
            <div className="flex flex-col gap-1">
              {task.status === 'pending' && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => onStatusChange?.(task.id, 'in_progress')}
                >
                  Start
                </Button>
              )}
              {task.status === 'in_progress' && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => onStatusChange?.(task.id, 'completed')}
                >
                  Complete
                </Button>
              )}
              {task.status !== 'completed' && task.status !== 'skipped' && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onStatusChange?.(task.id, 'skipped')}
                >
                  Skip
                </Button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
