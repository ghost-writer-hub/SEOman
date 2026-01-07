'use client';

import { useEffect, useState } from 'react';
import { Header } from '@/components/layout/Header';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Modal } from '@/components/ui/Modal';
import { Spinner } from '@/components/ui/Spinner';
import { Alert } from '@/components/ui/Alert';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { KeywordTable } from '@/components/keywords/KeywordTable';
import { KeywordDiscoverForm } from '@/components/keywords/KeywordDiscoverForm';
import { useKeywordsStore } from '@/stores/keywords';
import { useSitesStore } from '@/stores/sites';

export default function KeywordsPage() {
  const { keywords, clusters, isLoading, isDiscovering, error, fetchKeywords, fetchClusters, discoverKeywords, trackKeyword } = useKeywordsStore();
  const { sites, fetchSites } = useSitesStore();
  const [selectedSite, setSelectedSite] = useState('');
  const [isDiscoverModalOpen, setIsDiscoverModalOpen] = useState(false);

  useEffect(() => {
    fetchSites();
  }, [fetchSites]);

  useEffect(() => {
    if (selectedSite) {
      fetchKeywords(selectedSite);
      fetchClusters(selectedSite);
    }
  }, [fetchKeywords, fetchClusters, selectedSite]);

  // Auto-select first site
  useEffect(() => {
    if (sites.length > 0 && !selectedSite) {
      setSelectedSite(sites[0].id);
    }
  }, [sites, selectedSite]);

  const siteOptions = sites.map(site => ({ value: site.id, label: site.name }));

  const handleDiscover = async (seedKeywords: string[], location: string, language: string) => {
    await discoverKeywords({
      site_id: selectedSite,
      seed_keywords: seedKeywords,
      location,
      language,
    });
    setIsDiscoverModalOpen(false);
    fetchKeywords(selectedSite);
  };

  const handleTrack = async (id: string, track: boolean) => {
    await trackKeyword(id, track);
  };

  const trackedKeywords = keywords.filter(k => k.is_tracked);
  const untrackedKeywords = keywords.filter(k => !k.is_tracked);

  return (
    <div>
      <Header title="Keywords" />
      
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-4">
            <div className="w-64">
              <Select
                value={selectedSite}
                onChange={(e) => setSelectedSite(e.target.value)}
                options={siteOptions}
                placeholder="Select a site"
              />
            </div>
          </div>
          <Button onClick={() => setIsDiscoverModalOpen(true)} disabled={!selectedSite}>
            Discover Keywords
          </Button>
        </div>

        {error && (
          <Alert variant="error" className="mb-6">
            {error}
          </Alert>
        )}

        {!selectedSite ? (
          <div className="text-center py-12">
            <p className="text-gray-500">Select a site to view keywords</p>
          </div>
        ) : isLoading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : keywords.length === 0 ? (
          <div className="text-center py-12">
            <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No keywords yet</h3>
            <p className="text-gray-500 mb-4">Discover keywords to start tracking your rankings</p>
            <Button onClick={() => setIsDiscoverModalOpen(true)}>Discover Keywords</Button>
          </div>
        ) : (
          <Tabs defaultValue="all">
            <TabsList>
              <TabsTrigger value="all">All ({keywords.length})</TabsTrigger>
              <TabsTrigger value="tracked">Tracked ({trackedKeywords.length})</TabsTrigger>
              <TabsTrigger value="clusters">Clusters ({clusters.length})</TabsTrigger>
            </TabsList>
            
            <TabsContent value="all">
              <KeywordTable keywords={keywords} onTrack={handleTrack} />
            </TabsContent>
            
            <TabsContent value="tracked">
              {trackedKeywords.length > 0 ? (
                <KeywordTable keywords={trackedKeywords} onTrack={handleTrack} />
              ) : (
                <p className="text-center py-8 text-gray-500">No tracked keywords yet</p>
              )}
            </TabsContent>
            
            <TabsContent value="clusters">
              {clusters.length > 0 ? (
                <div className="space-y-4">
                  {clusters.map((cluster) => (
                    <div key={cluster.id} className="p-4 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-medium text-gray-900">{cluster.name}</h3>
                        <span className="text-sm text-gray-500 capitalize">{cluster.intent}</span>
                      </div>
                      {cluster.recommended_content_type && (
                        <p className="text-sm text-gray-600">
                          Recommended: {cluster.recommended_content_type}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center py-8 text-gray-500">No clusters yet. Add more keywords to enable clustering.</p>
              )}
            </TabsContent>
          </Tabs>
        )}
      </div>

      <Modal
        isOpen={isDiscoverModalOpen}
        onClose={() => setIsDiscoverModalOpen(false)}
        title="Discover Keywords"
        description="Enter seed keywords to discover related keyword opportunities"
      >
        <KeywordDiscoverForm
          onSubmit={handleDiscover}
          isLoading={isDiscovering}
        />
      </Modal>
    </div>
  );
}
