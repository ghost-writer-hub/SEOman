'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Header } from '@/components/layout/Header';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { Alert } from '@/components/ui/Alert';
import { AuditCard } from '@/components/audits/AuditCard';
import { useAuditsStore } from '@/stores/audits';
import { useSitesStore } from '@/stores/sites';

export default function AuditsPage() {
  const router = useRouter();
  const { audits, isLoading, error, fetchAudits } = useAuditsStore();
  const { sites, fetchSites } = useSitesStore();
  const [selectedSite, setSelectedSite] = useState('');

  useEffect(() => {
    fetchSites();
  }, [fetchSites]);

  useEffect(() => {
    fetchAudits(selectedSite || undefined);
  }, [fetchAudits, selectedSite]);

  const siteOptions = [
    { value: '', label: 'All Sites' },
    ...sites.map(site => ({ value: site.id, label: site.name })),
  ];

  const getSiteName = (siteId: string) => {
    const site = sites.find(s => s.id === siteId);
    return site?.name || 'Unknown Site';
  };

  return (
    <div>
      <Header title="SEO Audits" />
      
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <p className="text-gray-600">
            View and manage your SEO audit history
          </p>
          <div className="w-64">
            <Select
              value={selectedSite}
              onChange={(e) => setSelectedSite(e.target.value)}
              options={siteOptions}
            />
          </div>
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
        ) : audits.length === 0 ? (
          <div className="text-center py-12">
            <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No audits yet</h3>
            <p className="text-gray-500">Run an audit from the Sites page to get started</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {audits.map((audit) => (
              <AuditCard
                key={audit.id}
                audit={audit}
                siteName={getSiteName(audit.site_id)}
                onClick={() => router.push(`/audits/${audit.id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
