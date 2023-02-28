import blocks as bk
import consensus as cs
import blocks as bk
import config as cfg


class BuildProcessor:
    def __init__(self, epoch, broadcasts):
        self.epoch = epoch
        self.broadcasts = broadcasts
        self.block = None
        if self.broadcasts is not None and len(self.broadcasts) > 0:
            try:
                self.block = bk.Block(self.broadcasts, self.epoch)
            except bk.BlockEmptyException:
                if self.epoch in cfg.epoch_chain_commit:
                    del cfg.epoch_chain_commit[self.epoch]
        else:
            if self.epoch in cfg.epoch_chain_commit:
                del cfg.epoch_chain_commit[self.epoch]
            # 

    def finalize_block(self):
        """add final block to chain"""
        if self.block is None:
            print("~EMPTY EPOCH")
            return
        cs.add_block(self.block, self.epoch)
        if cfg.SHOW_BLOCK_INFO:
            print(
                f"~block_hash: {self.block.block_hash[:8]}...{self.block.block_hash[-8:]}"
            )
            print(
                "~block_engagements:",
                len(self.block.bc_body) if self.block.bc_body != "None" else 0,
            )
