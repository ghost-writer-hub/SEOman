'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/auth';
import { Spinner } from '@/components/ui/Spinner';

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, fetchUser, isLoading } = useAuthStore();

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        router.push('/dashboard');
      } else {
        router.push('/login');
      }
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 rounded-2xl bg-blue-600 text-white flex items-center justify-center text-3xl font-bold">
            S
          </div>
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">SEOman</h1>
        <p className="text-gray-600 mb-8">
          Multi-tenant SEO Platform with AI-powered analysis
        </p>
        <Spinner size="lg" />
      </div>
    </main>
  );
}
