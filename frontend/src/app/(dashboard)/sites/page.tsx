'use client';

import { useEffect, useState } from 'react';
import { Header } from '@/components/layout/Header';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Spinner } from '@/components/ui/Spinner';
import { Alert } from '@/components/ui/Alert';
import { SiteCard } from '@/components/sites/SiteCard';
import { SiteForm } from '@/components/sites/SiteForm';
import { useSitesStore } from '@/stores/sites';
import { useAuditsStore } from '@/stores/audits';
import type { Site } from '@/lib/types';

export default function SitesPage() {
  const { sites, isLoading, error, fetchSites, createSite, updateSite, deleteSite } = useSitesStore();
  const { createAudit } = useAuditsStore();
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSite, setEditingSite] = useState<Site | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchSites();
  }, [fetchSites]);

  const handleCreate = () => {
    setEditingSite(null);
    setIsModalOpen(true);
  };

  const handleEdit = (site: Site) => {
    setEditingSite(site);
    setIsModalOpen(true);
  };

  const handleDelete = async (site: Site) => {
    if (confirm(`Are you sure you want to delete "${site.name}"?`)) {
      await deleteSite(site.id);
    }
  };

  const handleAudit = async (site: Site) => {
    try {
      await createAudit({ site_id: site.id });
      alert('Audit started! Check the Audits page for progress.');
    } catch (err) {
      alert('Failed to start audit');
    }
  };

  const handleSubmit = async (data: Parameters<typeof createSite>[0]) => {
    setIsSubmitting(true);
    try {
      if (editingSite) {
        await updateSite(editingSite.id, data);
      } else {
        await createSite(data);
      }
      setIsModalOpen(false);
    } catch (err) {
      // Error handled by store
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <Header title="Sites" />
      
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <p className="text-gray-600">
            Manage your websites and run SEO audits
          </p>
          <Button onClick={handleCreate}>
            Add Site
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
        ) : sites.length === 0 ? (
          <div className="text-center py-12">
            <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No sites yet</h3>
            <p className="text-gray-500 mb-4">Add your first website to start tracking SEO performance</p>
            <Button onClick={handleCreate}>Add Your First Site</Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {sites.map((site) => (
              <SiteCard
                key={site.id}
                site={site}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onAudit={handleAudit}
              />
            ))}
          </div>
        )}
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingSite ? 'Edit Site' : 'Add New Site'}
      >
        <SiteForm
          site={editingSite || undefined}
          onSubmit={handleSubmit}
          onCancel={() => setIsModalOpen(false)}
          isLoading={isSubmitting}
        />
      </Modal>
    </div>
  );
}
