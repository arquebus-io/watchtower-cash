import logging
import web3
import requests
from celery import shared_task
from django.conf import settings
from django.db import models

from smartbch.conf import settings as app_settings
from smartbch.models import (
    Block,
    TransactionTransfer,
)
from smartbch.utils import block as block_utils
from smartbch.utils import subscription as subscription_utils
from smartbch.utils import transaction as transaction_utils
from smartbch.utils import contract as contract_utils

LOGGER = logging.getLogger(__name__)
REDIS_CLIENT = settings.REDISKV

## Redis names used
_REDIS_NAME__BLOCKS_BEING_PARSED = 'smartbch:blocks-being-parsed'
_REDIS_NAME__TXS_BEING_PARSED = 'smartbch:txs-being-parsed'
_REDIS_NAME__TXS_TRANSFERS_BEING_PARSED = 'smartbch:tx-transfers-being-parsed'
_REDIS_NAME__ADDRESS_BEING_CRAWLED = 'smartbch:address-being-crawled'

@shared_task
def preload_new_blocks_task():
    LOGGER.info("Preloading new blocks to db")

    (start_block, end_block) = block_utils.preload_new_blocks()
    LOGGER.info(f"Preloaded blocks from {start_block} to {end_block}")
    return (start_block, end_block)

@shared_task
def parse_blocks_task():
    LOGGER.info("Parsing new blocks")

    block_count = None
    if isinstance(app_settings.BLOCKS_PER_TASK, int):
        LOGGER.info(f"Using app settings for number of blocks to parse: {app_settings.BLOCKS_PER_TASK}")
        block_count = app_settings.BLOCKS_PER_TASK
    else:
        LOGGER.info(f"Using fallback settings for number of blocks to parse: 5")
        block_count = 5

    blocks_being_parsed = REDIS_CLIENT.smembers(_REDIS_NAME__BLOCKS_BEING_PARSED)
    blocks_being_parsed = [i.decode() for i in blocks_being_parsed]

    blocks = Block.objects.exclude(
        block_number__in=blocks_being_parsed
    ).exclude(
        processed=True
    ).order_by(
        'block_number'
    )[:block_count]

    LOGGER.info(f"Queueing blocks for parsing: {blocks.values_list('block_number', flat=True)}")
    for block_obj in blocks:
        parse_block_task.delay(block_obj.block_number, send_notifications=True)
    

@shared_task
def parse_block_task(block_number, send_notifications=False):
    LOGGER.info(f"Parsing block: {block_number}")
    LOGGER.info(f"Active blocks: {REDIS_CLIENT.smembers(_REDIS_NAME__BLOCKS_BEING_PARSED)}")

    try:
        block_number = int(block_number)
    except (TypeError, ValueError):
        LOGGER.info(f"Block number ({block_number}) is invalid")
        return f"invalid_block: {block_number}"

    if REDIS_CLIENT.exists(_REDIS_NAME__BLOCKS_BEING_PARSED, str(block_number)):
        LOGGER.info(f"Block number ({block_number}) is being parsed by another task, will stop task")
        return f"block_is_being_parsed {block_number}"

    REDIS_CLIENT.sadd(_REDIS_NAME__BLOCKS_BEING_PARSED, str(block_number))
    try:
        block_obj = block_utils.parse_block(block_number, save_transactions=True)
        LOGGER.info(f"Parsed block successfully: {block_obj}")

        LOGGER.info(f"Parsing transaction transfers under block: {block_obj}")
        for tx_obj in block_obj.transactions.all():
            save_transaction_transfers_task.delay(tx_obj.txid, send_notifications=send_notifications)

    except Exception as e:
        return f"parse_block_task({block_number}) error: {str(e)}"
    finally:
        REDIS_CLIENT.srem(_REDIS_NAME__BLOCKS_BEING_PARSED, str(block_number))


@shared_task
def save_transaction_transfers_task(txid, send_notifications=False):
    LOGGER.info(f"Parsing transaction transfers: {txid}")
    LOGGER.info(f"Active transaction: {REDIS_CLIENT.smembers(_REDIS_NAME__TXS_TRANSFERS_BEING_PARSED)}")

    if REDIS_CLIENT.exists(_REDIS_NAME__TXS_TRANSFERS_BEING_PARSED, str(txid)):
        LOGGER.info(f"Transaction ({txid}) is being parsed by another task, will stop task")
        return f"transaction_is_being_parsed: {txid}"

    REDIS_CLIENT.sadd(_REDIS_NAME__TXS_TRANSFERS_BEING_PARSED, str(txid))

    try:
        tx_obj = transaction_utils.save_transaction_transfers(str(txid))
        if tx_obj:
            LOGGER.info(f"Parsed transaction transfers successfully: {tx_obj}")
            if send_notifications:
                LOGGER.info(f"Queueing to send notfication for transaction: {tx_obj}")
                send_transaction_notification_task.delay(tx_obj.txid)

            return f"parsed transaction transfers: {txid}"
        else:
            LOGGER.info(f"Unable to parse transaction transfer, transaction is not saved: {tx_obj}")
            return f"Unable to parse transaction transfer, transaction is not saved: {tx_obj}"

    except Exception as e:
        return f"save_transaction_transfers_task({txid}) error: {str(e)}"
    finally:
        REDIS_CLIENT.srem(_REDIS_NAME__TXS_TRANSFERS_BEING_PARSED, str(txid))


@shared_task
def save_transaction_task(txid):
    LOGGER.info(f"Parsing transaction: {txid}")

    if REDIS_CLIENT.exists(_REDIS_NAME__TXS_BEING_PARSED, str(txid)):
        LOGGER.info(f"Transaction ({txid}) is being parsed by another task, will stop task")
        return f"transaction_is_being_parsed: {txid}"

    REDIS_CLIENT.sadd(_REDIS_NAME__TXS_BEING_PARSED, str(txid))

    try:
        tx_obj = transaction_utils.save_transaction(str(txid))
        LOGGER.info(f"Parsed transaction successfully: {tx_obj}")
        LOGGER.info(f"Queueing task for saving transaction transfers of: {tx_obj.txid}")
        save_transaction_transfers_task.delay(tx_obj.txid)
        return f"parsed transaction: {txid}"
    except Exception as e:
        return f"save_transaction_task({txid}) error: {str(e)}"
    finally:
        REDIS_CLIENT.srem(_REDIS_NAME__TXS_BEING_PARSED, str(txid))


@shared_task
def save_transactions_by_address(address):
    LOGGER.info(f"Crawling transactions of: {address}")
    if not web3.Web3.isAddress(address):
        LOGGER.info(f"Address ({address}) is invalid")
        return f"address_invalid: {address}"

    if REDIS_CLIENT.exists(_REDIS_NAME__ADDRESS_BEING_CRAWLED, str(address)):
        LOGGER.info(f"Address ({address}) is being parsed by another task, will stop task")
        return f"address_is_being_crawled: {address}"

    REDIS_CLIENT.sadd(_REDIS_NAME__ADDRESS_BEING_CRAWLED, str(address))

    # we expect other tasks to save the newer unprocessed blocks
    end_block = Block.objects.filter(processed=True).aggregate(latest_block = models.Max('block_number')).get('latest_block')

    is_numeric = lambda var: isinstance(var, (int, decimal.Decimal))
    start_block = app_settings.START_BLOCK
    if not is_numeric(start_block):
        start_block = Block.objects.filter(processed=True).aggregate(earliest_parsed_block = models.Min('block_number')).get('earliest_parsed_block')

    # just added a guard to limit the block to backtrack to 250 blocks
    if not is_numeric(start_block) or end_block - start_block > 250:
        start_block = end_block - 250

    iterator = transaction_utils.get_transactions_by_address(
        address,
        from_block=start_block,
        to_block=end_block,
        block_partition=10,
    )

    for tx_list in iterator:
        for tx in tx_list.transactions:
            save_transaction_task.delay(tx.hash)


@shared_task
def send_transaction_notification_task(txid):
    tx_obj = Transaction.objects.filter(txid=txid).first()

    if not tx_obj:
        return f"transaction with id {txid} does not exist"

    for transfer_tx in tx_obj.transfers.all():
        send_transaction_transfer_notification_task.delay(transfer_tx.id)


@shared_task(max_retries=3)
def send_transaction_transfer_notification_task(tx_transfer_id):
    tx_transfer_obj = TransactionTransfer.objects.filter(id=tx_transfer_id).first()

    if not tx_transfer_obj:
        return f"transaction_transfer with id {tx_transfer_id} does not exist"

    subscriptions = tx_transfer_obj.get_unsent_valid_subscriptions()

    if subscriptions is None or not subscriptions.exists():
        return f"transaction_transfer with id {tx_transfer_id} has no related valid subscriptions"

    if tx_transfer_obj.token_contract:
        contract_utils.get_or_save_token_contract_metadata(
            tx_transfer_obj.token_contract.address,
            force=False,
        )

    log_ids = []
    failed_subs = []
    for subscription in subscriptions:
        log, error = subscription_utils.send_transaction_transfer_notification_to_subscriber(
            subscription,
            tx_transfer_obj,
        )

        if log:
            log_ids.append(log.id)
        elif error:
            failed_subs.append(
                (subscription, error)
            )

    resp = []
    if len(log_ids):
        LOGGER.info(f"sucessfully sent subscription notifications: {log_ids}")
        resp.append(f"sent {len(log_ids)} transaction_transfer notifications, log_ids: {log_ids}")

    if len(failed_subs):
        LOGGER.info(f"Failed to send subscription notifications: {failed_subs}")
        resp.append(f"error sending {len(failed_subs)} transaction_transfer notifications: {failed_subs}")
        self.retry(countdown=3)

    return "\n".join(resp)
