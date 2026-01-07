'use client';

import { useState } from 'react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';

interface LoginFormProps {
  onSubmit: (email: string, password: string) => Promise<void>;
  onRegisterClick: () => void;
  isLoading?: boolean;
  error?: string;
}

export function LoginForm({ onSubmit, onRegisterClick, isLoading, error }: LoginFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(email, password);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <Alert variant="error">
          {error}
        </Alert>
      )}
      
      <Input
        label="Email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
        required
        autoComplete="email"
      />
      
      <Input
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="••••••••"
        required
        autoComplete="current-password"
      />
      
      <Button type="submit" className="w-full" isLoading={isLoading}>
        Sign In
      </Button>
      
      <p className="text-center text-sm text-gray-600">
        Don&apos;t have an account?{' '}
        <button
          type="button"
          onClick={onRegisterClick}
          className="text-blue-600 hover:text-blue-700 font-medium"
        >
          Sign up
        </button>
      </p>
    </form>
  );
}
