'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { RegisterForm } from '@/components/forms/RegisterForm';
import { useAuthStore } from '@/stores/auth';

export default function RegisterPage() {
  const router = useRouter();
  const { register, isAuthenticated, isLoading, error } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, router]);

  const handleRegister = async (email: string, password: string, fullName: string, tenantName: string) => {
    try {
      await register(email, password, fullName, tenantName);
      router.push('/dashboard');
    } catch (err) {
      // Error handled by store
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="w-12 h-12 rounded-xl bg-blue-600 text-white flex items-center justify-center text-xl font-bold">
              S
            </div>
          </div>
          <CardTitle className="text-2xl">Create your account</CardTitle>
          <CardDescription>Start your SEO journey with SEOman</CardDescription>
        </CardHeader>
        <CardContent>
          <RegisterForm
            onSubmit={handleRegister}
            onLoginClick={() => router.push('/login')}
            isLoading={isLoading}
            error={error || undefined}
          />
        </CardContent>
      </Card>
    </div>
  );
}
