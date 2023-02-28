import time

history = []
now = time.time()
for slot in range(10000000):
    # history.append(slot)
    # rm_num = ((slot + 2) & -(slot + 2)) // 2
    # # print(rm_num)
    # rm_epochs = history[-2:0:-2][:rm_num]
    # # print(rm_epochs)
    # # # print(rm_epochs)

    # for t in rm_epochs:
    #     history.remove(t)

    # print(history)
    # # print()

    history.append([slot])
    for i in range(len(history) - 2, 0, -1):
        if len(history[i - 1]) == len(history[i]) and len(history[i]) == len(
            history[i + 1]
        ):
            history[i - 1] += history.pop(i)
show = [b[0] for b in history]
print(time.time() - now)
print(show)
# for i,bucket in enumerate(history[-2:0:-1]):
#     if len(bucket) == len(history[i-1]) and len(bucket) == len(history[i+1]):
#         history[i-1]

