
# Benchmarking file I/O

This script test disk i/o performance using the tool fio.

Details are discussed in a blog post: [ZFS performance tuning](https://martin.heiland.io/2018/02/23/zfs-tuning/index.html)

In short, four tests are run for the block sizes {4k, 64k, 1M}. The four tests are random read, random write, sequential read, and sequential write.




