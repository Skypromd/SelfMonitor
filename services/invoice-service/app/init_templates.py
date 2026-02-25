#!/usr/bin/env python3
"""Initialize system templates for self-employed users"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .database import DATABASE_URL, Base
from .crud import create_system_templates
from .pdf_generator import PDFGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_tables():
    """Create database tables"""
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully")
    await engine.dispose()

async def initialize_templates():
    """Initialize system templates and default HTML template"""
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            # Create system templates for self-employed
            await create_system_templates(session)
            logger.info("System templates initialized successfully")
            
            # Create default PDF template
            pdf_generator = PDFGenerator()
            template_content = pdf_generator.create_default_template()
            
            # Save default template to file
            template_path = pdf_generator.template_dir / "default_invoice.html"
            template_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            
            logger.info(f"Default PDF template created at {template_path}")
            
        except Exception as e:
            logger.error(f"Error initializing templates: {e}")
            raise
        finally:
            await engine.dispose()

async def main():
    """Main initialization function"""
    logger.info("Starting invoice service initialization...")
    
    try:
        # Create database tables
        await create_tables()
        
        # Initialize templates
        await initialize_templates()
        
        logger.info("Invoice service initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())