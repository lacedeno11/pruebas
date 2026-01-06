# DERCAS-ONCO-XAI V1 - Image Service CRUD Operations
# Database CRUD operations for image metadata

from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from .models import Image
from .schemas import ImageFilters, PaginationParams

logger = structlog.get_logger(__name__)


class ImageCRUD:
    """CRUD operations for Image model."""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        image_data: Dict[str, Any],
        uploaded_by: Optional[str] = None
    ) -> Image:
        """
        Create a new image record.
        
        Args:
            db: Database session
            image_data: Image data dictionary
            uploaded_by: User uploading the image
            
        Returns:
            Created image
        """
        # Ensure uploaded_by is set
        if uploaded_by:
            image_data["uploaded_by"] = uploaded_by
            image_data["updated_by"] = uploaded_by
        
        image = Image(**image_data)
        
        db.add(image)
        await db.flush()
        await db.refresh(image)
        
        logger.info(
            "Image record created",
            image_id=image.id,
            filename=image.original_filename,
            format=image.file_format,
            size_mb=image.file_size_mb,
            uploaded_by=uploaded_by
        )
        
        return image
    
    @staticmethod
    async def get_by_id(db: AsyncSession, image_id: str) -> Optional[Image]:
        """
        Get image by ID.
        
        Args:
            db: Database session
            image_id: Image ID
            
        Returns:
            Image or None
        """
        result = await db.execute(
            select(Image).where(and_(Image.id == image_id, Image.is_active == True))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_storage_key(db: AsyncSession, storage_key: str) -> Optional[Image]:
        """
        Get image by storage key.
        
        Args:
            db: Database session
            storage_key: Storage key
            
        Returns:
            Image or None
        """
        result = await db.execute(
            select(Image).where(and_(
                Image.storage_key == storage_key,
                Image.is_active == True
            ))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_hash(db: AsyncSession, hash_value: str, hash_type: str = "md5") -> Optional[Image]:
        """
        Get image by hash value.
        
        Args:
            db: Database session
            hash_value: Hash value
            hash_type: Hash type ("md5" or "sha256")
            
        Returns:
            Image or None
        """
        if hash_type == "md5":
            condition = Image.md5_hash == hash_value
        elif hash_type == "sha256":
            condition = Image.sha256_hash == hash_value
        else:
            raise ValueError(f"Unsupported hash type: {hash_type}")
        
        result = await db.execute(
            select(Image).where(and_(condition, Image.is_active == True))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_images(
        db: AsyncSession,
        pagination: PaginationParams,
        filters: Optional[ImageFilters] = None,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[Image], int]:
        """
        List images with pagination and filtering.
        
        Args:
            db: Database session
            pagination: Pagination parameters
            filters: Filter parameters
            order_by: Field to order by
            order_desc: Whether to order descending
            
        Returns:
            Tuple of (images, total_count)
        """
        # Build base query
        query = select(Image).where(Image.is_active == True)
        count_query = select(func.count(Image.id)).where(Image.is_active == True)
        
        # Apply filters
        if filters:
            conditions = []
            
            if filters.case_id:
                conditions.append(Image.case_id == filters.case_id)
            
            if filters.file_format:
                conditions.append(Image.file_format == filters.file_format)
            
            if filters.modality:
                conditions.append(Image.modality == filters.modality)
            
            if filters.processing_status:
                conditions.append(Image.processing_status == filters.processing_status)
            
            if filters.has_thumbnail is not None:
                conditions.append(Image.has_thumbnail == filters.has_thumbnail)
            
            if filters.uploaded_by:
                conditions.append(Image.uploaded_by == filters.uploaded_by)
            
            if filters.created_after:
                conditions.append(Image.created_at >= filters.created_after)
            
            if filters.created_before:
                conditions.append(Image.created_at <= filters.created_before)
            
            if filters.min_file_size:
                conditions.append(Image.file_size >= filters.min_file_size)
            
            if filters.max_file_size:
                conditions.append(Image.file_size <= filters.max_file_size)
            
            if filters.min_width:
                conditions.append(Image.width >= filters.min_width)
            
            if filters.max_width:
                conditions.append(Image.width <= filters.max_width)
            
            if filters.min_height:
                conditions.append(Image.height >= filters.min_height)
            
            if filters.max_height:
                conditions.append(Image.height <= filters.max_height)
            
            if filters.search:
                search_term = f"%{filters.search}%"
                conditions.append(Image.original_filename.ilike(search_term))
            
            if filters.tags:
                # Filter by tags (JSONB contains)
                for tag in filters.tags:
                    conditions.append(Image.tags.contains([tag]))
            
            if conditions:
                filter_condition = and_(*conditions)
                query = query.where(filter_condition)
                count_query = count_query.where(filter_condition)
        
        # Apply ordering
        order_column = getattr(Image, order_by, Image.created_at)
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.size)
        
        # Execute queries
        result = await db.execute(query)
        images = result.scalars().all()
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        return list(images), total_count
    
    @staticmethod
    async def list_images_by_case(
        db: AsyncSession,
        case_id: str,
        pagination: PaginationParams,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[Image], int]:
        """
        List images for a specific case.
        
        Args:
            db: Database session
            case_id: Case ID
            pagination: Pagination parameters
            order_by: Field to order by
            order_desc: Whether to order descending
            
        Returns:
            Tuple of (images, total_count)
        """
        # Build query
        query = select(Image).where(
            and_(
                Image.case_id == case_id,
                Image.is_active == True
            )
        )
        count_query = select(func.count(Image.id)).where(
            and_(
                Image.case_id == case_id,
                Image.is_active == True
            )
        )
        
        # Apply ordering
        order_column = getattr(Image, order_by, Image.created_at)
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.size)
        
        # Execute queries
        result = await db.execute(query)
        images = result.scalars().all()
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        return list(images), total_count
    
    @staticmethod
    async def update(
        db: AsyncSession,
        image: Image,
        update_data: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> Image:
        """
        Update image.
        
        Args:
            db: Database session
            image: Image to update
            update_data: Update data
            updated_by: User updating the image
            
        Returns:
            Updated image
        """
        for field, value in update_data.items():
            if hasattr(image, field):
                setattr(image, field, value)
        
        image.updated_by = updated_by
        image.updated_at = datetime.utcnow()
        
        await db.flush()
        await db.refresh(image)
        
        logger.info(
            "Image updated",
            image_id=image.id,
            updated_by=updated_by
        )
        
        return image
    
    @staticmethod
    async def update_processing_status(
        db: AsyncSession,
        image: Image,
        status: str,
        error: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> Image:
        """
        Update image processing status.
        
        Args:
            db: Database session
            image: Image to update
            status: Processing status
            error: Error message if failed
            updated_by: User updating the image
            
        Returns:
            Updated image
        """
        image.update_processing_status(status, error)
        image.updated_by = updated_by
        image.updated_at = datetime.utcnow()
        
        await db.flush()
        
        logger.info(
            "Image processing status updated",
            image_id=image.id,
            status=status,
            updated_by=updated_by
        )
        
        return image
    
    @staticmethod
    async def increment_view_count(
        db: AsyncSession,
        image: Image
    ) -> Image:
        """
        Increment image view count.
        
        Args:
            db: Database session
            image: Image to update
            
        Returns:
            Updated image
        """
        image.increment_view_count()
        
        await db.flush()
        
        logger.debug(
            "Image view count incremented",
            image_id=image.id,
            view_count=image.view_count
        )
        
        return image
    
    @staticmethod
    async def delete(
        db: AsyncSession,
        image: Image,
        deleted_by: Optional[str] = None
    ) -> Image:
        """
        Soft delete image.
        
        Args:
            db: Database session
            image: Image to delete
            deleted_by: User deleting the image
            
        Returns:
            Deleted image
        """
        image.is_active = False
        image.updated_by = deleted_by
        image.updated_at = datetime.utcnow()
        
        await db.flush()
        
        logger.info(
            "Image deleted",
            image_id=image.id,
            deleted_by=deleted_by
        )
        
        return image
    
    @staticmethod
    async def get_image_statistics(db: AsyncSession) -> Dict[str, Any]:
        """
        Get image statistics.
        
        Args:
            db: Database session
            
        Returns:
            Statistics dictionary
        """
        # Total images
        total_result = await db.execute(
            select(func.count(Image.id)).where(Image.is_active == True)
        )
        total_images = total_result.scalar()
        
        # Total size
        size_result = await db.execute(
            select(func.sum(Image.file_size)).where(Image.is_active == True)
        )
        total_size = size_result.scalar() or 0
        
        # Images by format
        format_result = await db.execute(
            select(Image.file_format, func.count(Image.id))
            .where(Image.is_active == True)
            .group_by(Image.file_format)
        )
        format_counts = dict(format_result.all())
        
        # Images by modality
        modality_result = await db.execute(
            select(Image.modality, func.count(Image.id))
            .where(and_(Image.is_active == True, Image.modality.isnot(None)))
            .group_by(Image.modality)
        )
        modality_counts = dict(modality_result.all())
        
        # Images by processing status
        status_result = await db.execute(
            select(Image.processing_status, func.count(Image.id))
            .where(Image.is_active == True)
            .group_by(Image.processing_status)
        )
        status_counts = dict(status_result.all())
        
        # Images with thumbnails
        thumbnail_result = await db.execute(
            select(func.count(Image.id))
            .where(and_(Image.is_active == True, Image.has_thumbnail == True))
        )
        with_thumbnails = thumbnail_result.scalar()
        
        # Total views
        views_result = await db.execute(
            select(func.sum(Image.view_count)).where(Image.is_active == True)
        )
        total_views = views_result.scalar() or 0
        
        # Average dimensions
        avg_dimensions = None
        if total_images > 0:
            dimensions_result = await db.execute(
                select(
                    func.avg(Image.width).label("avg_width"),
                    func.avg(Image.height).label("avg_height")
                )
                .where(and_(
                    Image.is_active == True,
                    Image.width.isnot(None),
                    Image.height.isnot(None)
                ))
            )
            dimensions = dimensions_result.first()
            if dimensions and dimensions.avg_width and dimensions.avg_height:
                avg_dimensions = f"{int(dimensions.avg_width)}x{int(dimensions.avg_height)}"
        
        return {
            "total_images": total_images,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2),
            "by_format": format_counts,
            "by_modality": modality_counts,
            "by_processing_status": status_counts,
            "average_file_size_mb": round(total_size / (1024 * 1024) / total_images, 2) if total_images > 0 else 0,
            "average_dimensions": avg_dimensions,
            "with_thumbnails": with_thumbnails,
            "total_views": total_views
        }
    
    @staticmethod
    async def find_duplicates(db: AsyncSession, hash_type: str = "md5") -> List[Dict[str, Any]]:
        """
        Find duplicate images by hash.
        
        Args:
            db: Database session
            hash_type: Hash type to use for comparison
            
        Returns:
            List of duplicate groups
        """
        if hash_type == "md5":
            hash_column = Image.md5_hash
        elif hash_type == "sha256":
            hash_column = Image.sha256_hash
        else:
            raise ValueError(f"Unsupported hash type: {hash_type}")
        
        # Find hashes that appear more than once
        duplicate_hashes_result = await db.execute(
            select(hash_column, func.count(Image.id).label("count"))
            .where(Image.is_active == True)
            .group_by(hash_column)
            .having(func.count(Image.id) > 1)
        )
        
        duplicate_hashes = [row[0] for row in duplicate_hashes_result.all()]
        
        if not duplicate_hashes:
            return []
        
        # Get all images with duplicate hashes
        duplicates_result = await db.execute(
            select(Image)
            .where(and_(
                hash_column.in_(duplicate_hashes),
                Image.is_active == True
            ))
            .order_by(hash_column, Image.created_at)
        )
        
        duplicates = duplicates_result.scalars().all()
        
        # Group by hash
        duplicate_groups = {}
        for image in duplicates:
            hash_value = getattr(image, f"{hash_type}_hash")
            if hash_value not in duplicate_groups:
                duplicate_groups[hash_value] = []
            duplicate_groups[hash_value].append({
                "id": image.id,
                "filename": image.original_filename,
                "case_id": image.case_id,
                "file_size": image.file_size,
                "created_at": image.created_at,
                "uploaded_by": image.uploaded_by
            })
        
        return [
            {
                "hash": hash_value,
                "hash_type": hash_type,
                "count": len(images),
                "images": images
            }
            for hash_value, images in duplicate_groups.items()
        ]
