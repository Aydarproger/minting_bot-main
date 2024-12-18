import asyncio
from pytoniq_core import Address, Cell, begin_cell
from create_bot import client, wallet
from tonutils.nft import CollectionStandard
from tonutils.nft.content import OffchainContent
from tonutils.nft.content import OffchainCommonContent
from tonutils.nft.royalty_params import RoyaltyParams
from tonutils.nft.marketplace.getgems.contract.salev3r3 import SaleV3R3
from tonutils.wallet.data import TransferData


def get_addr():
    return wallet.address.to_str(False)


def calc_fee_amount(items_count: int):
    return 20000000 * items_count + 100000000 + 50000000 * items_count


async def wait_for_seqno():
    seqno = await wallet.get_seqno(client, wallet.address)
    new_seqno = seqno
    while new_seqno != seqno + 1:
        new_seqno = await wallet.get_seqno(client, wallet.address)
        await asyncio.sleep(1)
    return new_seqno


async def transfer_ownership(nft_collection_address, new_owner_address):
    transfer_message = (
        begin_cell()
        .store_uint(3, 32)
        .store_uint(0, 64)
        .store_address(new_owner_address)
    )
    await wallet.transfer(nft_collection_address, 0.01, transfer_message)


async def deploy_nft_collection(content_url, common_content_url, owner_addr):
    collection = CollectionStandard(
        owner_address=wallet.address,
        next_item_index=0,
        content=OffchainContent(
            uri=content_url,
            prefix_uri=common_content_url,
        ),
        royalty_params=RoyaltyParams(
            base=100,
            factor=10,
            address=Address(owner_addr),
        ),
    )

    await wallet.transfer(
        destination=collection.address,
        amount=0.01,
        state_init=collection.state_init,
    )
    return collection.address.to_str(is_user_friendly=False)


async def deploy_nft_items(items_count, collection_address):
    body = CollectionStandard.build_batch_mint_body(
        data=[
            (
                OffchainCommonContent(uri=f"{index}.json"),
                wallet.address,
            )
            for index in range(0, items_count)
        ],
        from_index=0,
        amount_per_one=10000000,
    )

    await wallet.transfer(
        destination=collection_address,
        amount=items_count * 2 / 100,
        body=body,
    )


async def put_nft_on_sale(collection_address: str, items_count, price, owner_addr):
    queue = []
    for item_index in range(items_count):
        flag = False
        while not flag:
            try:
                response = await client.run_get_method(
                    collection_address, "get_nft_address_by_index", [item_index]
                )
                rp_cell = Cell.one_from_boc(response["stack"][0]["value"]).begin_parse()
                nft_address = rp_cell.load_address()
                sale = SaleV3R3(
                    nft_address=nft_address,
                    owner_address=owner_addr,
                    marketplace_address="0:80fe687ad4c01291030951882ad75490075624c403c874fc207dbacfb02a8e24",
                    marketplace_fee_address="0:80fe687ad4c01291030951882ad75490075624c403c874fc207dbacfb02a8e24",
                    royalty_address=wallet.address,
                    marketplace_fee=price * 10**9 // 40,
                    royalty_fee=0,
                    price=price * 10**9 + price * 10**9 // 40,
                )
                body = sale.build_transfer_nft_body(
                    destination=Address(
                        # "EQAIFunALREOeQ99syMbO6sSzM_Fa1RsPD5TBoS0qVeKQ-AR"
                        "kQDZwUjVjK__PvChXCvtCMshBT1hrPKMwzRhyTAtonUbL9i9" # change for testnet
                    ),
                    owner_address=None,
                    state_init=sale.state_init,
                    amount=35000000,
                )
                queue.append(
                    TransferData(destination=nft_address, amount=0.1, body=body)
                )
                flag = True
            except Exception as e:
                print(e)
                await asyncio.sleep(2)
        if (item_index == items_count - 1) or (len(queue) == 4):
            seqno = await wallet.get_seqno(client, wallet.address)
            await wallet.batch_transfer(queue)
            new_seqno = seqno
            while new_seqno != seqno + 1:
                new_seqno = await wallet.get_seqno(client, wallet.address)
                await asyncio.sleep(1)
            queue = []
