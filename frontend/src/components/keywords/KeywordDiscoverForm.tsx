'use client';

import { useState } from 'react';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';

interface KeywordDiscoverFormProps {
  onSubmit: (seedKeywords: string[], location: string, language: string) => Promise<void>;
  isLoading?: boolean;
}

const locationOptions = [
  { value: 'United States', label: 'United States' },
  { value: 'United Kingdom', label: 'United Kingdom' },
  { value: 'Canada', label: 'Canada' },
  { value: 'Australia', label: 'Australia' },
  { value: 'Germany', label: 'Germany' },
  { value: 'France', label: 'France' },
  { value: 'Spain', label: 'Spain' },
];

const languageOptions = [
  { value: 'en', label: 'English' },
  { value: 'de', label: 'German' },
  { value: 'fr', label: 'French' },
  { value: 'es', label: 'Spanish' },
  { value: 'it', label: 'Italian' },
  { value: 'pt', label: 'Portuguese' },
];

export function KeywordDiscoverForm({ onSubmit, isLoading }: KeywordDiscoverFormProps) {
  const [keywords, setKeywords] = useState('');
  const [location, setLocation] = useState('United States');
  const [language, setLanguage] = useState('en');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const seedKeywords = keywords
      .split('\n')
      .map(k => k.trim())
      .filter(k => k.length > 0);
    
    if (seedKeywords.length === 0) return;
    
    await onSubmit(seedKeywords, location, language);
    setKeywords('');
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Seed Keywords (one per line)
        </label>
        <textarea
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          className="w-full h-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="seo tools&#10;keyword research&#10;backlink checker"
          required
        />
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Location"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          options={locationOptions}
        />
        
        <Select
          label="Language"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          options={languageOptions}
        />
      </div>
      
      <Button type="submit" isLoading={isLoading} className="w-full">
        Discover Keywords
      </Button>
    </form>
  );
}
