"""
Database validator to fix chain ID issues on startup.
This module validates and fixes database inconsistencies automatically.
"""

import logging
from typing import Dict, Any, Optional
from pymongo.database import Database
from pymongo.collection import Collection

logger = logging.getLogger(__name__)

# Chain name to ID mapping for fixing old data
CHAIN_NAME_TO_ID = {
    "ethereum": 1,
    "polygon": 137,
    "bsc": 56,
    "arbitrum": 42161,
    "optimism": 10,
    "avalanche": 43114,
    "fantom": 250,
    "cronos": 25,
    "polygon_mumbai": 80001,
    "ethereum_goerli": 5,
    "bsc_testnet": 97,
    "arbitrum_goerli": 421613,
    "optimism_goerli": 420,
}

def validate_and_fix_chain_ids(db: Optional[Database]) -> Dict[str, int]:
    """
    Validate and fix chain ID issues in the database.
    
    Args:
        db: MongoDB database instance
        
    Returns:
        Dict with statistics about what was fixed
    """
    if db is None:
        logger.warning("Database not available for validation")
        return {"fixed": 0, "deleted": 0, "errors": 0}
    
    stats = {"fixed": 0, "deleted": 0, "errors": 0}
    
    try:
        # Fix swaps collection
        swaps_stats = _fix_swaps_collection(db.swaps)
        stats["fixed"] += swaps_stats["fixed"]
        stats["deleted"] += swaps_stats["deleted"]
        stats["errors"] += swaps_stats["errors"]
        
        # Fix DCA jobs collection
        dca_stats = _fix_dca_collection(db.dca_jobs)
        stats["fixed"] += dca_stats["fixed"]
        stats["deleted"] += dca_stats["deleted"]
        stats["errors"] += dca_stats["errors"]
        
        # Fix baskets collection
        baskets_stats = _fix_baskets_collection(db.baskets)
        stats["fixed"] += baskets_stats["fixed"]
        stats["deleted"] += baskets_stats["deleted"]
        stats["errors"] += baskets_stats["errors"]
        
        if stats["fixed"] > 0 or stats["deleted"] > 0:
            logger.info(f"Database validation completed: {stats['fixed']} records fixed, {stats['deleted']} records deleted, {stats['errors']} errors")
        else:
            logger.info("Database validation completed: No issues found")
            
    except Exception as e:
        logger.error(f"Error during database validation: {e}")
        stats["errors"] += 1
    
    return stats

def _fix_swaps_collection(swaps_collection: Collection) -> Dict[str, int]:
    """Fix chain ID issues in swaps collection."""
    stats = {"fixed": 0, "deleted": 0, "errors": 0}
    
    try:
        # Find all swaps with string chain IDs
        string_chain_swaps = swaps_collection.find({
            "$or": [
                {"src_chain": {"$type": "string"}},
                {"dst_chain": {"$type": "string"}}
            ]
        })
        
        for swap in string_chain_swaps:
            try:
                swap_id = swap.get("_id")
                src_chain = swap.get("src_chain")
                dst_chain = swap.get("dst_chain")
                
                # Try to fix src_chain
                if isinstance(src_chain, str):
                    if src_chain in CHAIN_NAME_TO_ID:
                        new_src_chain = CHAIN_NAME_TO_ID[src_chain]
                        swaps_collection.update_one(
                            {"_id": swap_id},
                            {"$set": {"src_chain": new_src_chain}}
                        )
                        logger.info(f"Fixed swap {swap_id}: src_chain '{src_chain}' -> {new_src_chain}")
                        stats["fixed"] += 1
                    else:
                        # Delete swaps with unknown chain names
                        swaps_collection.delete_one({"_id": swap_id})
                        logger.warning(f"Deleted swap {swap_id}: unknown src_chain '{src_chain}'")
                        stats["deleted"] += 1
                
                # Try to fix dst_chain
                if isinstance(dst_chain, str):
                    if dst_chain in CHAIN_NAME_TO_ID:
                        new_dst_chain = CHAIN_NAME_TO_ID[dst_chain]
                        swaps_collection.update_one(
                            {"_id": swap_id},
                            {"$set": {"dst_chain": new_dst_chain}}
                        )
                        logger.info(f"Fixed swap {swap_id}: dst_chain '{dst_chain}' -> {new_dst_chain}")
                        stats["fixed"] += 1
                    else:
                        # Delete swaps with unknown chain names
                        swaps_collection.delete_one({"_id": swap_id})
                        logger.warning(f"Deleted swap {swap_id}: unknown dst_chain '{dst_chain}'")
                        stats["deleted"] += 1

            except Exception as e:
                logger.error(f"Error fixing swap {swap.get('_id')}: {e}")
                stats["errors"] += 1

        # Populate missing chain_id using src_chain when available
        missing_chain_id = swaps_collection.find({"chain_id": {"$exists": False}})
        for swap in missing_chain_id:
            try:
                swap_id = swap.get("_id")
                src_chain = swap.get("src_chain")
                if isinstance(src_chain, str):
                    src_chain = CHAIN_NAME_TO_ID.get(src_chain)
                if isinstance(src_chain, int):
                    swaps_collection.update_one({"_id": swap_id}, {"$set": {"chain_id": src_chain}})
                    stats["fixed"] += 1
            except Exception as e:
                logger.error(f"Error setting chain_id for swap {swap.get('_id')}: {e}")
                stats["errors"] += 1

                
    except Exception as e:
        logger.error(f"Error processing swaps collection: {e}")
        stats["errors"] += 1
    
    return stats

def _fix_dca_collection(dca_collection: Collection) -> Dict[str, int]:
    """Fix chain ID issues in DCA jobs collection."""
    stats = {"fixed": 0, "deleted": 0, "errors": 0}
    
    try:
        # Find all DCA jobs with string chain IDs
        string_chain_dca = dca_collection.find({
            "$or": [
                {"src_chain": {"$type": "string"}},
                {"dst_chain": {"$type": "string"}}
            ]
        })
        
        for dca in string_chain_dca:
            try:
                dca_id = dca.get("_id")
                src_chain = dca.get("src_chain")
                dst_chain = dca.get("dst_chain")
                
                # Try to fix src_chain
                if isinstance(src_chain, str):
                    if src_chain in CHAIN_NAME_TO_ID:
                        new_src_chain = CHAIN_NAME_TO_ID[src_chain]
                        dca_collection.update_one(
                            {"_id": dca_id},
                            {"$set": {"src_chain": new_src_chain}}
                        )
                        logger.info(f"Fixed DCA {dca_id}: src_chain '{src_chain}' -> {new_src_chain}")
                        stats["fixed"] += 1
                    else:
                        # Delete DCA jobs with unknown chain names
                        dca_collection.delete_one({"_id": dca_id})
                        logger.warning(f"Deleted DCA {dca_id}: unknown src_chain '{src_chain}'")
                        stats["deleted"] += 1
                
                # Try to fix dst_chain
                if isinstance(dst_chain, str):
                    if dst_chain in CHAIN_NAME_TO_ID:
                        new_dst_chain = CHAIN_NAME_TO_ID[dst_chain]
                        dca_collection.update_one(
                            {"_id": dca_id},
                            {"$set": {"dst_chain": new_dst_chain}}
                        )
                        logger.info(f"Fixed DCA {dca_id}: dst_chain '{dst_chain}' -> {new_dst_chain}")
                        stats["fixed"] += 1
                    else:
                        # Delete DCA jobs with unknown chain names
                        dca_collection.delete_one({"_id": dca_id})
                        logger.warning(f"Deleted DCA {dca_id}: unknown dst_chain '{dst_chain}'")
                        stats["deleted"] += 1
                        
            except Exception as e:
                logger.error(f"Error fixing DCA {dca.get('_id')}: {e}")
                stats["errors"] += 1
                
    except Exception as e:
        logger.error(f"Error processing DCA collection: {e}")
        stats["errors"] += 1
    
    return stats

def _fix_baskets_collection(baskets_collection: Collection) -> Dict[str, int]:
    """Fix chain ID issues in baskets collection."""
    stats = {"fixed": 0, "deleted": 0, "errors": 0}
    
    try:
        # Find all baskets with string chain IDs
        string_chain_baskets = baskets_collection.find({
            "$or": [
                {"src_chain": {"$type": "string"}},
                {"dst_chain": {"$type": "string"}}
            ]
        })
        
        for basket in string_chain_baskets:
            try:
                basket_id = basket.get("_id")
                src_chain = basket.get("src_chain")
                dst_chain = basket.get("dst_chain")
                
                # Try to fix src_chain
                if isinstance(src_chain, str):
                    if src_chain in CHAIN_NAME_TO_ID:
                        new_src_chain = CHAIN_NAME_TO_ID[src_chain]
                        baskets_collection.update_one(
                            {"_id": basket_id},
                            {"$set": {"src_chain": new_src_chain}}
                        )
                        logger.info(f"Fixed basket {basket_id}: src_chain '{src_chain}' -> {new_src_chain}")
                        stats["fixed"] += 1
                    else:
                        # Delete baskets with unknown chain names
                        baskets_collection.delete_one({"_id": basket_id})
                        logger.warning(f"Deleted basket {basket_id}: unknown src_chain '{src_chain}'")
                        stats["deleted"] += 1
                
                # Try to fix dst_chain
                if isinstance(dst_chain, str):
                    if dst_chain in CHAIN_NAME_TO_ID:
                        new_dst_chain = CHAIN_NAME_TO_ID[dst_chain]
                        baskets_collection.update_one(
                            {"_id": basket_id},
                            {"$set": {"dst_chain": new_dst_chain}}
                        )
                        logger.info(f"Fixed basket {basket_id}: dst_chain '{dst_chain}' -> {new_dst_chain}")
                        stats["fixed"] += 1
                    else:
                        # Delete baskets with unknown chain names
                        baskets_collection.delete_one({"_id": basket_id})
                        logger.warning(f"Deleted basket {basket_id}: unknown dst_chain '{dst_chain}'")
                        stats["deleted"] += 1
                        
            except Exception as e:
                logger.error(f"Error fixing basket {basket.get('_id')}: {e}")
                stats["errors"] += 1
                
    except Exception as e:
        logger.error(f"Error processing baskets collection: {e}")
        stats["errors"] += 1
    
    return stats

def run_database_validation(db: Optional[Database]) -> None:
    """
    Run database validation on startup.
    This function should be called when the application starts.
    
    Args:
        db: MongoDB database instance (can be None if not connected)
    """
    if db is not None:
        logger.info("Starting database validation...")
        stats = validate_and_fix_chain_ids(db)
        if stats["fixed"] > 0 or stats["deleted"] > 0:
            logger.info(f"Database cleanup completed: {stats}")
    else:
        logger.info("Database not connected, skipping validation") 