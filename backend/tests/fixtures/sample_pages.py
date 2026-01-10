"""
Sample page fixtures for testing.
"""

# Perfect SEO page - should pass most checks
PERFECT_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Perfect SEO Page - Complete with All Elements</title>
    <meta name="description" content="This is a perfectly optimized meta description that is exactly the right length for search engine results pages and user engagement.">
    <link rel="canonical" href="https://example.com/perfect-page">
    <meta name="robots" content="index, follow">

    <!-- Open Graph -->
    <meta property="og:title" content="Perfect SEO Page">
    <meta property="og:description" content="Optimized for social sharing">
    <meta property="og:image" content="https://example.com/og-image.jpg">
    <meta property="og:url" content="https://example.com/perfect-page">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Perfect SEO Page">

    <!-- Structured Data -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "Perfect SEO Page",
        "description": "A page with perfect SEO optimization",
        "url": "https://example.com/perfect-page"
    }
    </script>
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/about">About Us</a>
            <a href="/services">Our Services</a>
            <a href="/contact">Contact</a>
        </nav>
    </header>

    <main>
        <h1>Perfect SEO Page Title</h1>

        <p>This is the main content of the page. It contains valuable information
        that users are looking for when they search for related keywords.</p>

        <h2>Section One - Important Topic</h2>
        <p>Detailed content about the first important topic. This section provides
        comprehensive information that helps users understand the subject matter.</p>

        <h2>Section Two - Another Key Topic</h2>
        <p>More valuable content covering another important aspect of the main topic.
        This helps search engines understand the page structure and content hierarchy.</p>

        <h3>Subsection - Specific Details</h3>
        <p>Even more detailed information about specific aspects of the topic.</p>

        <img src="/images/relevant-image.jpg" alt="Descriptive alt text for the image" width="800" height="600">

        <p>The page continues with more valuable content that provides depth and
        substance to the topic being discussed.</p>
    </main>

    <footer>
        <p>&copy; 2026 Example Company. All rights reserved.</p>
    </footer>
</body>
</html>
"""

# Poor SEO page - should fail multiple checks
POOR_SEO_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Bad</title>
</head>
<body>
    <p>Short content.</p>
    <img src="/image.jpg">
    <a href="click here">more</a>
</body>
</html>
"""

# SPA page - should trigger JS rendering detection
SPA_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>React App</title>
</head>
<body>
    <div id="root"></div>
    <script src="/static/js/main.chunk.js"></script>
    <script src="/static/js/bundle.js"></script>
</body>
</html>
"""

# Page with security issues
INSECURE_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Insecure Page</title>
    <script src="http://insecure-cdn.com/script.js"></script>
</head>
<body>
    <img src="http://example.com/image.jpg">
    <iframe src="http://insecure-site.com/embed"></iframe>
</body>
</html>
"""

# E-commerce product page
PRODUCT_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Amazing Widget - Only $29.99 | Example Store</title>
    <meta name="description" content="Buy the Amazing Widget for just $29.99. Free shipping on orders over $50. High quality, great reviews.">
    <link rel="canonical" href="https://example.com/products/amazing-widget">

    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Amazing Widget",
        "description": "The best widget you'll ever buy",
        "offers": {
            "@type": "Offer",
            "price": "29.99",
            "priceCurrency": "USD"
        }
    }
    </script>
</head>
<body>
    <h1>Amazing Widget</h1>
    <p>Product description goes here with detailed information about features and benefits.</p>
    <img src="/products/widget.jpg" alt="Amazing Widget - Front View" width="500" height="500">
</body>
</html>
"""

# Blog article page
BLOG_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>How to Optimize Your Website for SEO - Complete Guide 2026</title>
    <meta name="description" content="Learn the complete guide to SEO optimization in 2026. Cover technical SEO, content optimization, and link building strategies.">
    <link rel="canonical" href="https://example.com/blog/seo-optimization-guide">

    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": "How to Optimize Your Website for SEO",
        "datePublished": "2026-01-10",
        "author": {
            "@type": "Person",
            "name": "SEO Expert"
        }
    }
    </script>
</head>
<body>
    <article>
        <h1>How to Optimize Your Website for SEO</h1>
        <p>Published on January 10, 2026 by SEO Expert</p>

        <h2>Introduction</h2>
        <p>Search engine optimization is crucial for any website...</p>

        <h2>Technical SEO</h2>
        <p>Technical SEO covers the foundation of your website...</p>

        <h2>Content Optimization</h2>
        <p>Quality content is the key to ranking success...</p>
    </article>
</body>
</html>
"""

# Sample crawl data for testing
def get_sample_crawl_pages():
    """Return sample crawl page data."""
    return [
        {
            "url": "https://example.com",
            "status_code": 200,
            "title": "Example Website - Home",
            "meta_description": "Welcome to our example website with great content and services.",
            "h1": ["Welcome to Example"],
            "h2": ["About Us", "Our Services", "Latest News"],
            "word_count": 800,
            "canonical_url": "https://example.com",
            "internal_links": [
                {"url": "https://example.com/about", "text": "About Us"},
                {"url": "https://example.com/services", "text": "Services"},
                {"url": "https://example.com/blog", "text": "Blog"},
                {"url": "https://example.com/contact", "text": "Contact"},
            ],
            "external_links": [
                {"url": "https://twitter.com/example", "text": "Twitter"},
            ],
            "images": [
                {"url": "https://example.com/hero.jpg", "alt": "Hero Image", "width": 1200, "height": 600},
            ],
            "structured_data": [
                {"@type": "Organization", "name": "Example Inc", "url": "https://example.com"},
            ],
            "open_graph": {"og:title": "Example Website", "og:image": "https://example.com/og.jpg"},
            "twitter_cards": {"twitter:card": "summary_large_image"},
            "html_lang": "en",
            "has_viewport_meta": True,
            "viewport_content": "width=device-width, initial-scale=1",
            "noindex": False,
            "load_time_ms": 450,
        },
        {
            "url": "https://example.com/about",
            "status_code": 200,
            "title": "About Us - Example Website",
            "meta_description": "Learn more about Example Inc and our mission to provide excellent services.",
            "h1": ["About Our Company"],
            "h2": ["Our Mission", "Our Team", "Our History"],
            "word_count": 600,
            "canonical_url": "https://example.com/about",
            "internal_links": [
                {"url": "https://example.com", "text": "Home"},
                {"url": "https://example.com/contact", "text": "Contact Us"},
            ],
            "images": [
                {"url": "https://example.com/team.jpg", "alt": "Our Team"},
            ],
            "structured_data": [],
            "html_lang": "en",
            "has_viewport_meta": True,
            "noindex": False,
        },
        {
            "url": "https://example.com/services",
            "status_code": 200,
            "title": "Services",  # Too short
            "meta_description": "",  # Missing
            "h1": [],  # Missing
            "word_count": 150,  # Thin content
            "canonical_url": "https://example.com/services",
            "internal_links": [],  # No internal links
            "images": [
                {"url": "https://example.com/service.jpg", "alt": ""},  # Missing alt
            ],
            "structured_data": [],
            "html_lang": "",  # Missing
            "has_viewport_meta": False,  # Missing viewport
            "noindex": False,
        },
    ]
