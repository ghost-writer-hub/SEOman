'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Header } from '@/components/layout/Header';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { Alert } from '@/components/ui/Alert';
import { PlanCard } from '@/components/plans/PlanCard';
import { usePlansStore } from '@/stores/plans';
import { useSitesStore } from '@/stores/sites';

export default function PlansPage() {
  const router = useRouter();
  const { plans, isLoading, isGenerating, error, fetchPlans, generatePlan } = usePlansStore();
  const { sites, fetchSites } = useSitesStore();
  const [selectedSite, setSelectedSite] = useState('');

  useEffect(() => {
    fetchSites();
  }, [fetchSites]);

  useEffect(() => {
    fetchPlans(selectedSite || undefined);
  }, [fetchPlans, selectedSite]);

  const siteOptions = [
    { value: '', label: 'All Sites' },
    ...sites.map(site => ({ value: site.id, label: site.name })),
  ];

  const handleGeneratePlan = async () => {
    if (!selectedSite) {
      alert('Please select a site first');
      return;
    }
    
    try {
      const plan = await generatePlan(selectedSite);
      router.push(`/plans/${plan.id}`);
    } catch (err) {
      // Error handled by store
    }
  };

  return (
    <div>
      <Header title="SEO Plans" />
      
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-4">
            <div className="w-64">
              <Select
                value={selectedSite}
                onChange={(e) => setSelectedSite(e.target.value)}
                options={siteOptions}
              />
            </div>
          </div>
          <Button onClick={handleGeneratePlan} isLoading={isGenerating} disabled={!selectedSite}>
            Generate AI Plan
          </Button>
        </div>

        {error && (
          <Alert variant="error" className="mb-6">
            {error}
          </Alert>
        )}

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : plans.length === 0 ? (
          <div className="text-center py-12">
            <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No SEO plans yet</h3>
            <p className="text-gray-500 mb-4">Generate an AI-powered SEO plan to improve your rankings</p>
            <Button onClick={handleGeneratePlan} disabled={!selectedSite}>
              Generate Your First Plan
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {plans.map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                onClick={() => router.push(`/plans/${plan.id}`)}
                onEdit={() => router.push(`/plans/${plan.id}/edit`)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
