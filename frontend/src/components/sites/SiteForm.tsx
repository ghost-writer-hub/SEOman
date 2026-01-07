'use client';

import { useState } from 'react';
import type { Site, SiteCreate, SiteUpdate } from '@/lib/types';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';

interface SiteFormProps {
  site?: Site;
  onSubmit: (data: SiteCreate | SiteUpdate) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
}

const scheduleOptions = [
  { value: '', label: 'Manual (No Schedule)' },
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
];

export function SiteForm({ site, onSubmit, onCancel, isLoading }: SiteFormProps) {
  const [formData, setFormData] = useState({
    name: site?.name || '',
    url: site?.url || '',
    description: site?.description || '',
    audit_schedule: site?.audit_schedule || '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }
    
    if (!formData.url.trim()) {
      newErrors.url = 'URL is required';
    } else {
      try {
        new URL(formData.url);
      } catch {
        newErrors.url = 'Please enter a valid URL';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validate()) return;
    
    await onSubmit({
      name: formData.name,
      url: formData.url,
      description: formData.description || undefined,
      audit_schedule: formData.audit_schedule || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        label="Site Name"
        value={formData.name}
        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
        error={errors.name}
        placeholder="My Website"
        required
      />
      
      <Input
        label="URL"
        type="url"
        value={formData.url}
        onChange={(e) => setFormData({ ...formData, url: e.target.value })}
        error={errors.url}
        placeholder="https://example.com"
        required
      />
      
      <Input
        label="Description"
        value={formData.description}
        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
        placeholder="Optional description..."
      />
      
      <Select
        label="Audit Schedule"
        value={formData.audit_schedule}
        onChange={(e) => setFormData({ ...formData, audit_schedule: e.target.value })}
        options={scheduleOptions}
      />
      
      <div className="flex justify-end gap-3 pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" isLoading={isLoading}>
          {site ? 'Update Site' : 'Add Site'}
        </Button>
      </div>
    </form>
  );
}
