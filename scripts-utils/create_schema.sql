-- Create elsiebrain database schema
-- Updated to include categories array for enhanced page classification

-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS page_metadata CASCADE;
DROP TABLE IF EXISTS wiki_pages CASCADE;

-- Create wiki_pages table
CREATE TABLE wiki_pages (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    raw_content TEXT NOT NULL,
    url VARCHAR(500),
    crawl_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    touched TIMESTAMP, -- MediaWiki last modification timestamp
    categories TEXT[] NOT NULL, -- Array of category names for enhanced classification
    content_accessed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create page_metadata table
CREATE TABLE page_metadata (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    last_crawled TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    crawl_count INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'active',
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_wiki_pages_title ON wiki_pages(title);
CREATE INDEX idx_wiki_pages_touched ON wiki_pages(touched); -- Index for incremental updates
CREATE INDEX idx_wiki_pages_categories ON wiki_pages USING GIN (categories); -- GIN index for array search
CREATE INDEX idx_page_metadata_url ON page_metadata(url);
CREATE INDEX idx_page_metadata_hash ON page_metadata(content_hash);

-- Show tables created
\dt

-- Show sample data
SELECT COUNT(*) as total_pages FROM wiki_pages;
SELECT page_type, COUNT(*) as count FROM wiki_pages GROUP BY page_type;

COMMIT; 