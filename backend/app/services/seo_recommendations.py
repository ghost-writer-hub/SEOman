"""
SEO Recommendations with Code Examples

Provides detailed, actionable recommendations with code snippets for each SEO issue.
"""

from typing import Dict, Any, List


def get_detailed_recommendation(check_name: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get detailed recommendation with code examples for a specific check.

    Returns:
        Dict with 'description', 'why_it_matters', 'how_to_fix', and 'code_example'
    """
    details = details or {}

    recommendations = {
        # =========================================================================
        # Crawlability & Indexability
        # =========================================================================
        "Robots.txt Presence": {
            "description": "Your site is missing a robots.txt file, which helps search engines understand which pages to crawl.",
            "why_it_matters": "Without robots.txt, search engines may crawl inefficiently or access pages you don't want indexed.",
            "how_to_fix": "Create a robots.txt file in your site's root directory.",
            "code_example": """```txt
# robots.txt - Place in site root (e.g., https://example.com/robots.txt)
User-agent: *
Allow: /

# Block admin and private areas
Disallow: /admin/
Disallow: /private/
Disallow: /api/

# Point to sitemap
Sitemap: https://example.com/sitemap.xml
```"""
        },

        "Robots.txt Blocking Critical Resources": {
            "description": "Your robots.txt is blocking CSS, JavaScript, or image files that search engines need to render your pages.",
            "why_it_matters": "Google renders pages like a browser. Blocking these resources prevents proper indexing and can hurt rankings.",
            "how_to_fix": "Remove Disallow rules for static resources.",
            "code_example": """```txt
# BAD - Don't do this:
User-agent: *
Disallow: /css/
Disallow: /js/
Disallow: *.css$
Disallow: *.js$

# GOOD - Allow crawlers to access resources:
User-agent: *
Allow: /css/
Allow: /js/
Allow: /images/
Disallow: /admin/
```"""
        },

        "Noindex Tags on Important Pages": {
            "description": "Important pages have noindex meta tags, preventing them from appearing in search results.",
            "why_it_matters": "Pages with noindex will never rank in Google, regardless of their content quality.",
            "how_to_fix": "Remove the noindex directive from pages you want indexed.",
            "code_example": """```html
<!-- REMOVE this tag from important pages: -->
<meta name="robots" content="noindex, nofollow">

<!-- Or if using X-Robots-Tag header, remove it from server config: -->
<!-- Apache .htaccess - REMOVE: -->
Header set X-Robots-Tag "noindex, nofollow"

<!-- For pages you DO want to noindex (thank you pages, etc.): -->
<meta name="robots" content="noindex, follow">
```"""
        },

        "Canonical Tag Presence": {
            "description": "Pages are missing canonical tags, which can lead to duplicate content issues.",
            "why_it_matters": "Without canonical tags, search engines may split ranking signals between duplicate URLs.",
            "how_to_fix": "Add self-referencing canonical tags to all indexable pages.",
            "code_example": """```html
<head>
  <!-- Add canonical tag pointing to the preferred URL -->
  <link rel="canonical" href="https://www.example.com/page-url/">

  <!-- For paginated content: -->
  <link rel="canonical" href="https://www.example.com/blog/">
  <link rel="prev" href="https://www.example.com/blog/page/1/">
  <link rel="next" href="https://www.example.com/blog/page/3/">
</head>
```"""
        },

        "Canonical Self-Referencing": {
            "description": "Canonical tags point to different URLs instead of the page itself.",
            "why_it_matters": "Incorrect canonicals can transfer all ranking signals to the wrong page.",
            "how_to_fix": "Ensure each page's canonical points to itself (unless intentionally consolidating).",
            "code_example": """```html
<!-- On https://www.example.com/products/widget/ -->

<!-- WRONG - Points to different URL: -->
<link rel="canonical" href="https://example.com/products/widget">

<!-- CORRECT - Self-referencing with exact URL: -->
<link rel="canonical" href="https://www.example.com/products/widget/">

<!-- PHP/Dynamic example: -->
<link rel="canonical" href="<?php echo 'https://' . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI']; ?>">
```"""
        },

        "Orphan Pages": {
            "description": "Pages exist but have no internal links pointing to them.",
            "why_it_matters": "Orphan pages are hard for search engines to discover and typically receive little PageRank.",
            "how_to_fix": "Add internal links from related pages, navigation, or footer.",
            "code_example": """```html
<!-- Option 1: Add to main navigation -->
<nav>
  <a href="/orphan-page/">Previously Orphaned Page</a>
</nav>

<!-- Option 2: Add contextual links from related content -->
<article>
  <p>Learn more about this topic in our
    <a href="/orphan-page/">detailed guide</a>.
  </p>
</article>

<!-- Option 3: Add to HTML sitemap or footer -->
<footer>
  <a href="/orphan-page/">Useful Resource</a>
</footer>
```"""
        },

        # =========================================================================
        # On-Page SEO
        # =========================================================================
        "Missing Title Tag": {
            "description": "Pages are missing title tags, one of the most important on-page SEO elements.",
            "why_it_matters": "Title tags are the #1 on-page ranking factor and appear as the clickable headline in search results.",
            "how_to_fix": "Add unique, descriptive title tags between 50-60 characters.",
            "code_example": """```html
<head>
  <!-- Format: Primary Keyword - Secondary Keyword | Brand Name -->
  <title>Hotel Booking in Barcelona - Best Rates Guaranteed | O7 Hotels</title>

  <!-- Keep under 60 characters to avoid truncation -->
  <!-- Include target keyword near the beginning -->
  <!-- Make it compelling and click-worthy -->
</head>
```"""
        },

        "Title Too Short (<30 chars)": {
            "description": "Title tags are too short to effectively describe page content and target keywords.",
            "why_it_matters": "Short titles miss opportunities to include keywords and attract clicks.",
            "how_to_fix": "Expand titles to 50-60 characters with relevant keywords.",
            "code_example": """```html
<!-- BAD - Too short (15 chars): -->
<title>O7 Hotels</title>

<!-- GOOD - Descriptive (58 chars): -->
<title>O7 Hotels - Beachfront Resorts in Mallorca & Tenerife</title>

<!-- Template for product/service pages: -->
<title>[Product/Service] - [Benefit/Location] | [Brand]</title>
```"""
        },

        "Title Too Long (>60 chars)": {
            "description": "Title tags exceed 60 characters and will be truncated in search results.",
            "why_it_matters": "Truncated titles look unprofessional and may cut off important keywords.",
            "how_to_fix": "Shorten titles to under 60 characters while keeping key information.",
            "code_example": """```html
<!-- BAD - Too long (85 chars, will be truncated): -->
<title>Best Luxury Beach Hotels and All-Inclusive Resorts in Mallorca, Spain - Book Now</title>

<!-- GOOD - Concise (56 chars): -->
<title>Luxury Beach Hotels in Mallorca | All-Inclusive Resorts</title>

<!-- Tip: Use pipes (|) or dashes (-) to separate sections -->
```"""
        },

        "Duplicate Title Tags": {
            "description": "Multiple pages share the same title tag, confusing search engines.",
            "why_it_matters": "Duplicate titles compete with each other and dilute ranking potential.",
            "how_to_fix": "Create unique titles for each page based on its specific content.",
            "code_example": """```html
<!-- BAD - Same title on multiple pages: -->
<!-- /mallorca/ --> <title>O7 Hotels</title>
<!-- /tenerife/ --> <title>O7 Hotels</title>

<!-- GOOD - Unique titles per page: -->
<!-- /mallorca/ --> <title>Hotels in Mallorca - Beach Resorts & Family Holidays | O7</title>
<!-- /tenerife/ --> <title>Tenerife Hotels - All-Inclusive Resorts & Deals | O7</title>

<!-- Dynamic template (PHP example): -->
<title><?php echo $page_title; ?> | O7 Hotels</title>
```"""
        },

        "Missing Meta Description": {
            "description": "Pages lack meta descriptions, letting Google auto-generate snippets.",
            "why_it_matters": "Well-written meta descriptions improve click-through rates from search results.",
            "how_to_fix": "Add compelling meta descriptions of 150-160 characters.",
            "code_example": """```html
<head>
  <meta name="description" content="Book your dream beach holiday at O7 Hotels Mallorca. All-inclusive resorts, stunning sea views, and family-friendly amenities. Best price guaranteed!">

  <!-- Guidelines:
       - 150-160 characters (Google truncates longer)
       - Include primary keyword naturally
       - Add a call-to-action
       - Make it unique for each page
  -->
</head>
```"""
        },

        "Missing H1": {
            "description": "Pages are missing H1 headings, the main topic indicator for search engines.",
            "why_it_matters": "H1 tags tell search engines and users what the page is about.",
            "how_to_fix": "Add a single, descriptive H1 tag at the top of each page's content.",
            "code_example": """```html
<body>
  <header>
    <!-- Logo and navigation here -->
  </header>

  <main>
    <!-- Add H1 as the main heading (only one per page) -->
    <h1>Beachfront Hotels in Mallorca</h1>

    <p>Discover our collection of stunning resorts...</p>

    <!-- Use H2, H3 for subheadings -->
    <h2>Our Mallorca Locations</h2>
    <h3>Palma Beach Resort</h3>
  </main>
</body>
```"""
        },

        "Multiple H1s": {
            "description": "Pages have multiple H1 tags, diluting the main topic signal.",
            "why_it_matters": "Multiple H1s can confuse search engines about the page's primary topic.",
            "how_to_fix": "Use only one H1 per page; convert others to H2 or lower.",
            "code_example": """```html
<!-- BAD - Multiple H1s: -->
<h1>Welcome to O7 Hotels</h1>
<h1>Our Destinations</h1>
<h1>Special Offers</h1>

<!-- GOOD - Single H1 with H2 subheadings: -->
<h1>O7 Hotels - Luxury Beach Resorts</h1>
<h2>Our Destinations</h2>
<h3>Mallorca</h3>
<h3>Tenerife</h3>
<h2>Special Offers</h2>
```"""
        },

        "Missing Image Alt Text": {
            "description": "Images are missing alt text, hurting accessibility and image SEO.",
            "why_it_matters": "Alt text helps visually impaired users and allows images to rank in Google Images.",
            "how_to_fix": "Add descriptive alt text to all meaningful images.",
            "code_example": """```html
<!-- BAD - Missing or empty alt: -->
<img src="hotel-pool.jpg">
<img src="hotel-pool.jpg" alt="">

<!-- GOOD - Descriptive alt text: -->
<img src="hotel-pool.jpg"
     alt="Infinity pool overlooking the Mediterranean Sea at O7 Mallorca Resort">

<!-- For decorative images, use empty alt: -->
<img src="decorative-divider.png" alt="" role="presentation">

<!-- Include keywords naturally, don't stuff: -->
<img src="room.jpg" alt="Deluxe ocean-view room with king bed and private balcony">
```"""
        },

        # =========================================================================
        # Technical Performance
        # =========================================================================
        "TTFB > 800ms": {
            "description": f"Server response time exceeds 800ms (current average: {details.get('average_ttfb_ms', 'N/A')}ms).",
            "why_it_matters": "Slow TTFB delays everything else - rendering, Core Web Vitals, and user experience.",
            "how_to_fix": "Optimize server performance, database queries, and consider caching.",
            "code_example": """```apache
# Apache - Enable caching and compression
# .htaccess file:

# Enable compression
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/css application/javascript
</IfModule>

# Browser caching
<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresByType text/html "access plus 1 hour"
  ExpiresByType image/jpeg "access plus 1 year"
  ExpiresByType text/css "access plus 1 month"
</IfModule>
```

```nginx
# Nginx - Enable caching
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Enable gzip
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```"""
        },

        "Missing Image Dimensions": {
            "description": "Images lack width and height attributes, causing layout shifts.",
            "why_it_matters": "Missing dimensions cause CLS (Cumulative Layout Shift), hurting Core Web Vitals.",
            "how_to_fix": "Add width and height attributes to all images.",
            "code_example": """```html
<!-- BAD - No dimensions (causes layout shift): -->
<img src="hero.jpg" alt="Hotel exterior">

<!-- GOOD - Explicit dimensions: -->
<img src="hero.jpg" alt="Hotel exterior" width="1200" height="800">

<!-- With responsive CSS (maintains aspect ratio): -->
<style>
  img {
    max-width: 100%;
    height: auto;
  }
</style>
<img src="hero.jpg" alt="Hotel exterior" width="1200" height="800">

<!-- Modern approach with aspect-ratio: -->
<style>
  .hero-image {
    aspect-ratio: 3 / 2;
    width: 100%;
    object-fit: cover;
  }
</style>
```"""
        },

        # =========================================================================
        # URL Structure
        # =========================================================================
        "Duplicate Content URLs": {
            "description": "Multiple URLs serve identical or near-identical content.",
            "why_it_matters": "Duplicate content splits ranking signals and wastes crawl budget.",
            "how_to_fix": "Use 301 redirects or canonical tags to consolidate.",
            "code_example": """```apache
# Apache .htaccess - Redirect duplicates to canonical URL

# Redirect non-www to www
RewriteEngine On
RewriteCond %{HTTP_HOST} ^example\.com [NC]
RewriteRule ^(.*)$ https://www.example.com/$1 [L,R=301]

# Redirect trailing slash inconsistency
RewriteCond %{REQUEST_FILENAME} !-d
RewriteCond %{REQUEST_URI} (.+)/$
RewriteRule ^ %1 [L,R=301]

# Redirect HTTP to HTTPS
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
```

```nginx
# Nginx - Redirect duplicates
server {
    listen 80;
    server_name example.com www.example.com;
    return 301 https://www.example.com$request_uri;
}
```"""
        },

        # =========================================================================
        # Internal Linking
        # =========================================================================
        "Broken Internal Links (404)": {
            "description": "Internal links point to pages that return 404 errors.",
            "why_it_matters": "Broken links waste crawl budget, hurt user experience, and leak PageRank.",
            "how_to_fix": "Fix or remove broken links; implement redirects for moved pages.",
            "code_example": """```html
<!-- Find and fix broken links: -->

<!-- Option 1: Update the href to correct URL -->
<a href="/correct-page/">Link Text</a>

<!-- Option 2: Remove the link if page no longer exists -->
<span>Previously linked content</span>

<!-- Option 3: Add redirect in .htaccess for moved pages -->
```

```apache
# .htaccess - Redirect old URLs to new locations
Redirect 301 /old-page/ /new-page/
Redirect 301 /removed-page/ /relevant-alternative/

# Pattern-based redirects
RedirectMatch 301 ^/blog/old-category/(.*)$ /blog/new-category/$1
```"""
        },

        "Nofollow on Internal Links": {
            "description": "Internal links have rel='nofollow', blocking PageRank flow.",
            "why_it_matters": "Nofollow wastes your own PageRank instead of passing it to important pages.",
            "how_to_fix": "Remove nofollow from internal links.",
            "code_example": """```html
<!-- BAD - Nofollow on internal link: -->
<a href="/important-page/" rel="nofollow">Important Page</a>

<!-- GOOD - Normal internal link: -->
<a href="/important-page/">Important Page</a>

<!-- Only use nofollow for: -->
<!-- - User-generated content (comments, forums) -->
<!-- - Paid links -->
<!-- - Untrusted external links -->
<a href="https://external-site.com" rel="nofollow">External Link</a>
```"""
        },

        "Generic Anchor Text": {
            "description": "Links use generic text like 'click here' or 'read more' instead of descriptive anchors.",
            "why_it_matters": "Descriptive anchor text helps search engines understand linked page topics.",
            "how_to_fix": "Use descriptive, keyword-rich anchor text.",
            "code_example": """```html
<!-- BAD - Generic anchors: -->
<a href="/mallorca-hotels/">Click here</a>
<a href="/booking/">Read more</a>
<a href="/offers/">Learn more</a>

<!-- GOOD - Descriptive anchors: -->
<a href="/mallorca-hotels/">explore our Mallorca beach hotels</a>
<a href="/booking/">book your holiday now</a>
<a href="/offers/">view current special offers</a>

<!-- Balance keywords with natural language: -->
<p>Discover our <a href="/mallorca-hotels/">beachfront hotels in Mallorca</a>,
   featuring stunning sea views and all-inclusive packages.</p>
```"""
        },

        "Missing Breadcrumbs": {
            "description": "Pages lack breadcrumb navigation and structured data.",
            "why_it_matters": "Breadcrumbs improve UX, internal linking, and can appear in search results.",
            "how_to_fix": "Add breadcrumb navigation with Schema.org markup.",
            "code_example": """```html
<!-- Breadcrumb HTML with Schema.org JSON-LD -->
<nav aria-label="Breadcrumb">
  <ol class="breadcrumb">
    <li><a href="/">Home</a></li>
    <li><a href="/destinations/">Destinations</a></li>
    <li><a href="/destinations/mallorca/">Mallorca</a></li>
    <li aria-current="page">O7 Beach Resort</li>
  </ol>
</nav>

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "name": "Home",
      "item": "https://www.example.com/"
    },
    {
      "@type": "ListItem",
      "position": 2,
      "name": "Destinations",
      "item": "https://www.example.com/destinations/"
    },
    {
      "@type": "ListItem",
      "position": 3,
      "name": "Mallorca",
      "item": "https://www.example.com/destinations/mallorca/"
    },
    {
      "@type": "ListItem",
      "position": 4,
      "name": "O7 Beach Resort"
    }
  ]
}
</script>
```"""
        },

        # =========================================================================
        # Content Quality
        # =========================================================================
        "Missing OpenGraph Tags": {
            "description": "Pages lack OpenGraph meta tags for social media sharing.",
            "why_it_matters": "Without OG tags, social shares look unprofessional with wrong images/text.",
            "how_to_fix": "Add OpenGraph tags to all important pages.",
            "code_example": """```html
<head>
  <!-- Essential OpenGraph tags -->
  <meta property="og:title" content="Luxury Beach Hotels in Mallorca | O7 Hotels">
  <meta property="og:description" content="Book your dream Mediterranean getaway. Stunning beachfront resorts with all-inclusive packages.">
  <meta property="og:image" content="https://www.example.com/images/og-mallorca-hotel.jpg">
  <meta property="og:url" content="https://www.example.com/mallorca/">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="O7 Hotels">

  <!-- Recommended image size: 1200x630px -->
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">

  <!-- Twitter Card tags -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Luxury Beach Hotels in Mallorca">
  <meta name="twitter:description" content="Book your dream Mediterranean getaway.">
  <meta name="twitter:image" content="https://www.example.com/images/twitter-mallorca.jpg">
</head>
```"""
        },

        # =========================================================================
        # Structured Data
        # =========================================================================
        "Missing FAQ Schema": {
            "description": "FAQ pages lack FAQPage structured data.",
            "why_it_matters": "FAQ schema can display expandable Q&A directly in search results.",
            "how_to_fix": "Add FAQPage JSON-LD to pages with FAQ content.",
            "code_example": """```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What time is check-in?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Check-in time is 3:00 PM. Early check-in may be available upon request."
      }
    },
    {
      "@type": "Question",
      "name": "Is breakfast included?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes, a full buffet breakfast is included with all room bookings."
      }
    },
    {
      "@type": "Question",
      "name": "Do you have a swimming pool?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "We have 3 pools: an infinity pool, a family pool, and a heated indoor pool."
      }
    }
  ]
}
</script>
```"""
        },

        "Missing Breadcrumb Schema": {
            "description": "Inner pages lack BreadcrumbList structured data.",
            "why_it_matters": "Breadcrumb schema helps Google show site hierarchy in search results.",
            "how_to_fix": "Add BreadcrumbList JSON-LD to all inner pages.",
            "code_example": """```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "name": "Home",
      "item": "https://www.o7hotels.com/"
    },
    {
      "@type": "ListItem",
      "position": 2,
      "name": "Destinations",
      "item": "https://www.o7hotels.com/destinations/"
    },
    {
      "@type": "ListItem",
      "position": 3,
      "name": "Mallorca Hotels"
    }
  ]
}
</script>
```"""
        },

        # =========================================================================
        # Security & Accessibility
        # =========================================================================
        "Missing/Invalid Hreflang": {
            "description": "Multilingual pages have incorrect or missing hreflang tags.",
            "why_it_matters": "Proper hreflang prevents duplicate content issues and shows correct language versions in search.",
            "how_to_fix": "Add complete, bidirectional hreflang tags including self-reference.",
            "code_example": """```html
<head>
  <!-- On Spanish page: https://www.example.com/es/hoteles/ -->
  <link rel="alternate" hreflang="es" href="https://www.example.com/es/hoteles/">
  <link rel="alternate" hreflang="en" href="https://www.example.com/en/hotels/">
  <link rel="alternate" hreflang="de" href="https://www.example.com/de/hotels/">
  <link rel="alternate" hreflang="x-default" href="https://www.example.com/en/hotels/">

  <!-- IMPORTANT:
       - Include self-referencing tag (es points to current es page)
       - x-default for users with no language match
       - All language versions must link to each other
  -->
</head>

<!-- On English page: https://www.example.com/en/hotels/ -->
<head>
  <link rel="alternate" hreflang="es" href="https://www.example.com/es/hoteles/">
  <link rel="alternate" hreflang="en" href="https://www.example.com/en/hotels/">
  <link rel="alternate" hreflang="de" href="https://www.example.com/de/hotels/">
  <link rel="alternate" hreflang="x-default" href="https://www.example.com/en/hotels/">
</head>
```"""
        },

        "Missing Language Declaration": {
            "description": "HTML tag is missing the lang attribute.",
            "why_it_matters": "Language declaration helps screen readers and search engines understand content language.",
            "how_to_fix": "Add lang attribute to the HTML tag.",
            "code_example": """```html
<!-- Add lang attribute to html tag -->
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <!-- ... -->
</head>

<!-- Common language codes: -->
<!-- lang="en" - English -->
<!-- lang="es" - Spanish -->
<!-- lang="de" - German -->
<!-- lang="fr" - French -->
<!-- lang="en-GB" - British English -->
<!-- lang="es-ES" - Spanish (Spain) -->
```"""
        },

        # =========================================================================
        # Mobile Optimization
        # =========================================================================
        "Missing Viewport Meta": {
            "description": "Pages lack viewport meta tag for mobile responsiveness.",
            "why_it_matters": "Without viewport meta, pages won't scale properly on mobile devices.",
            "how_to_fix": "Add the viewport meta tag to all pages.",
            "code_example": """```html
<head>
  <meta charset="UTF-8">
  <!-- Add this viewport meta tag -->
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page Title</title>
</head>

<!-- This tells mobile browsers to:
     - Set viewport width to device width
     - Start at 1x zoom
     - Allow user to zoom in/out
-->
```"""
        },

        "Viewport Not Responsive": {
            "description": "Viewport meta tag doesn't include responsive settings.",
            "why_it_matters": "Incorrect viewport settings cause mobile usability issues and hurt mobile rankings.",
            "how_to_fix": "Set viewport to width=device-width, initial-scale=1.",
            "code_example": """```html
<!-- BAD - Fixed width or missing device-width: -->
<meta name="viewport" content="width=1024">
<meta name="viewport" content="initial-scale=1">

<!-- GOOD - Responsive viewport: -->
<meta name="viewport" content="width=device-width, initial-scale=1">

<!-- Also acceptable (with zoom control): -->
<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

<!-- Avoid disabling zoom (accessibility issue): -->
<!-- DON'T: maximum-scale=1, user-scalable=no -->
```"""
        },

        # =========================================================================
        # Server & Infrastructure
        # =========================================================================
        "4xx Errors": {
            "description": "The site has pages returning 4xx error codes (404, 403, etc.).",
            "why_it_matters": "Error pages waste crawl budget and indicate poor site maintenance.",
            "how_to_fix": "Fix broken URLs, add redirects, or remove links to error pages.",
            "code_example": """```apache
# .htaccess - Redirect 404s to appropriate pages

# Specific redirects
Redirect 301 /old-page.html /new-page/
Redirect 301 /removed-product/ /products/

# Custom 404 page
ErrorDocument 404 /404.html

# Redirect patterns
RedirectMatch 301 ^/blog/category/(.*)$ /blog/$1
```

```html
<!-- Create a helpful 404.html page: -->
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Page Not Found | O7 Hotels</title>
</head>
<body>
  <h1>Page Not Found</h1>
  <p>Sorry, we couldn't find that page. Here are some helpful links:</p>
  <ul>
    <li><a href="/">Home</a></li>
    <li><a href="/destinations/">Our Destinations</a></li>
    <li><a href="/contact/">Contact Us</a></li>
  </ul>
  <!-- Include search box if available -->
</body>
</html>
```"""
        },

        "Slow Server Response": {
            "description": "Server response times exceed acceptable thresholds.",
            "why_it_matters": "Slow servers directly impact Core Web Vitals and user experience.",
            "how_to_fix": "Implement caching, optimize database, consider CDN.",
            "code_example": """```php
<?php
// PHP - Enable output buffering and caching
ob_start();

// Database query caching
$cache_key = 'hotels_list_' . md5($query);
$result = apcu_fetch($cache_key);
if ($result === false) {
    $result = $db->query($query)->fetchAll();
    apcu_store($cache_key, $result, 3600); // Cache for 1 hour
}
?>
```

```nginx
# Nginx - FastCGI caching
fastcgi_cache_path /tmp/nginx levels=1:2 keys_zone=CACHE:100m inactive=60m;
fastcgi_cache_key "$scheme$request_method$host$request_uri";

location ~ \.php$ {
    fastcgi_cache CACHE;
    fastcgi_cache_valid 200 60m;
    fastcgi_cache_use_stale error timeout;
}
```

```apache
# Apache - Enable mod_cache
<IfModule mod_cache.c>
    CacheQuickHandler off
    CacheLock on
    CacheRoot /tmp/cache
    CacheEnable disk /
    CacheDefaultExpire 3600
</IfModule>
```"""
        },
    }

    # Return the recommendation if found, otherwise return a generic one
    if check_name in recommendations:
        return recommendations[check_name]

    # Generic fallback
    return {
        "description": f"Issue detected: {check_name}",
        "why_it_matters": "This issue may impact your site's SEO performance.",
        "how_to_fix": "Review the affected pages and implement the suggested fix.",
        "code_example": None
    }


def enhance_issue_with_recommendation(issue: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance an issue dict with detailed recommendation.

    Args:
        issue: Original issue dict with 'title', 'recommendation', 'details', etc.

    Returns:
        Enhanced issue dict with 'detailed_recommendation' field
    """
    check_name = issue.get("title", issue.get("check_name", ""))
    details = issue.get("details", {})

    detailed = get_detailed_recommendation(check_name, details)
    issue["detailed_recommendation"] = detailed

    return issue
