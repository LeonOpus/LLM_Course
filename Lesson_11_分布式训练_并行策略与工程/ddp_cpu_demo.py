"""单机两个 CPU 进程验证 DDP：分片、梯度同步及单进程结果对照。"""
import os
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, TensorDataset, DistributedSampler
from train_trainer import SimpleNet


def main():
    dist.init_process_group(backend='gloo')
    try:
        rank = dist.get_rank()
        world = dist.get_world_size()
        if world != 2:
            raise ValueError('这个演示需要两个进程：torchrun --standalone --nproc_per_node=2 ddp_cpu_demo.py')
        torch.set_num_threads(1)
        torch.manual_seed(11)
        x = torch.randn(8, 10)
        y = torch.randn(8, 2)
        model = SimpleNet(10, 20, 2)
        initial = {k: v.detach().clone() for k, v in model.state_dict().items()}
        ddp = DDP(model)
        data = TensorDataset(x, y)
        sampler = DistributedSampler(data, num_replicas=world, rank=rank, shuffle=False)
        indices = list(sampler)
        loader = DataLoader(data, batch_size=4, sampler=sampler)
        optimizer = torch.optim.SGD(ddp.parameters(), lr=0.05)
        inputs, labels = next(iter(loader))
        loss = torch.nn.functional.mse_loss(ddp(inputs), labels)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        print(f'rank={rank}, world_size={world}, 样本索引={indices}, 本地loss={loss.item():.6f}', flush=True)
        all_indices = [None] * world
        dist.all_gather_object(all_indices, indices)
        local = torch.cat([p.detach().flatten() for p in ddp.module.parameters()])
        copies = [torch.empty_like(local) for _ in range(world)]
        dist.all_gather(copies, local)
        assert torch.allclose(copies[0], copies[1], atol=1e-7)
        if rank == 0:
            assert sorted(sum(all_indices, [])) == list(range(8))
            reference = SimpleNet(10, 20, 2)
            reference.load_state_dict(initial)
            opt = torch.optim.SGD(reference.parameters(), lr=0.05)
            opt.zero_grad()
            torch.nn.functional.mse_loss(reference(x), y).backward()
            opt.step()
            reference_weights = torch.cat([p.detach().flatten() for p in reference.parameters()])
            diff = (local - reference_weights).abs().max().item()
            print(f'两进程参数一致；与单进程全批次更新的最大差值={diff:.9g}', flush=True)
            assert diff < 1e-6
        dist.barrier()
    finally:
        dist.destroy_process_group()


if __name__ == '__main__':
    main()
