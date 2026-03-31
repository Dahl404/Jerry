params_from_: Chat format: peg-native
slot get_availabl: id  3 | task -1 | selected slot by LCP similarity, sim_best = 0.981 (> 0.100 thold), f_keep = 0.980
slot launch_slot_: id  3 | task -1 | sampler chain: logits -> ?penalties -> ?dry -> ?top-n-sigma -> top-k -> ?typical -> top-p -> min-p -> ?xtc -> temp-ext -> dist
slot launch_slot_: id  3 | task 3031 | processing task, is_child = 0
slot update_slots: id  3 | task 3031 | new prompt, n_ctx_slot = 8192, n_keep = 0, task.n_tokens = 5403
slot update_slots: id  3 | task 3031 | n_past = 5302, slot.prompt.tokens.size() = 5411, seq_id = 3, pos_min = 5410, n_swa = 1
slot update_slots: id  3 | task 3031 | Checking checkpoint with [4790, 4790] against 5301...
slot update_slots: id  3 | task 3031 | restored context checkpoint (pos_min = 4790, pos_max = 4790, n_tokens = 4791, size = 50.251 MiB)
slot update_slots: id  3 | task 3031 | n_tokens = 4791, memory_seq_rm [4791, end)
slot update_slots: id  3 | task 3031 | prompt processing progress, n_tokens = 4891, batch.n_tokens = 100, progress = 0.905238
slot update_slots: id  3 | task 3031 | n_tokens = 4891, memory_seq_rm [4891, end)
slot init_sampler: id  3 | task 3031 | init sampler, took 2.41 ms, tokens: text = 5403, total = 5403
slot update_slots: id  3 | task 3031 | prompt processing done, n_tokens = 5403, batch.n_tokens = 512
slot update_slots: id  3 | task 3031 | created context checkpoint 11 of 32 (pos_min = 4890, pos_max = 4890, n_tokens = 4891, size = 50.251 MiB)
srv  log_server_r: done request: POST /v1/chat/completions 127.0.0.1 200
slot print_timing: id  3 | task 3031 |
prompt eval time =   26636.81 ms /   612 tokens (   43.52 ms per token,    22.98 tokens per second)
       eval time =    5028.35 ms /    26 tokens (  193.40 ms per token,     5.17 tokens per second)
      total time =   31665.17 ms /   638 tokens
slot      release: id  3 | task 3031 | stop processing: n_tokens = 5428, truncated = 0
srv  update_slots: all slots are idle
srv    operator(): got exception: {"error":{"code":400,"message":"Assistant response prefill is incompatible with enable_thinking.","type":"invalid_request_error"}}
srv  log_server_r: done request: POST /v1/chat/completions 127.0.0.1 400
srv    operator(): got exception: {"error":{"code":400,"message":"Assistant response prefill is incompatible with enable_thinking.","type":"invalid_request_error"}}
srv  log_server_r: done request: POST /v1/chat/completions 127.0.0.1 400
srv    operator(): got exception: {"error":{"code":400,"message":"Assistant response prefill is incompatible with enable_thinking.","type":"invalid_request_error"}}
srv  log_server_r: done request: POST /v1/chat/completions 127.0.0.1 400
srv    operator(): got exception: {"error":{"code":400,"message":"Assistant response prefill is incompatible with enable_thinking.","type":"invalid_request_error"}}
srv  log_server_r: done request: POST /v1/chat/completions 127.0.0.1 400
srv    operator(): got exception: {"error":{"code":400,"message":"Assistant response prefill is incompatible with enable_thinking.","type":"invalid_request_error"}}
srv  log_server_r: done request: POST /v1/chat/completions 127.0.0.1 400
srv    operator(): got exception: {"error":{"code":400,"message":"Assistant response prefill is incompatible with enable_thinking.","type":"invalid_request_error"}}
srv  log_server_r: done request: POST /v1/chat/completions 127.0.0.1 400
srv    operator(): got exception: {"error":{"code":400,"message":"Assistant response prefill is incompatible with enable_thinking.","type":"invalid_request_error"}}
srv  log_server_r: done request: POST /v1/chat/completions 127.0.0.1 400
srv    operator(): got exception: {"error":{"code":400,"message":"Assistant response prefill is incompatible with enable_thinking.","type":"invalid_request_error"}}
srv  log_server_r: done request: POST /v1/chat/completions 127.0.0.1 400







	
