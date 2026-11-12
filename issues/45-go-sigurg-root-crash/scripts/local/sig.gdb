set pagination off
set language c
set $b = (char*)($rsp - 16384)
call ((int(*)(int,void*,void*))__sigaction)(2, 0, (void*)$b)
printf "SIG 2 handler=%#lx flags=%#x ONSTACK=%d  ", *(unsigned long*)$b, *(unsigned int*)($b+136), ((*(unsigned int*)($b+136)) & 0x08000000) != 0
info symbol *(unsigned long*)$b
call ((int(*)(int,void*,void*))__sigaction)(6, 0, (void*)$b)
printf "SIG 6 handler=%#lx flags=%#x ONSTACK=%d  ", *(unsigned long*)$b, *(unsigned int*)($b+136), ((*(unsigned int*)($b+136)) & 0x08000000) != 0
info symbol *(unsigned long*)$b
call ((int(*)(int,void*,void*))__sigaction)(7, 0, (void*)$b)
printf "SIG 7 handler=%#lx flags=%#x ONSTACK=%d  ", *(unsigned long*)$b, *(unsigned int*)($b+136), ((*(unsigned int*)($b+136)) & 0x08000000) != 0
info symbol *(unsigned long*)$b
call ((int(*)(int,void*,void*))__sigaction)(8, 0, (void*)$b)
printf "SIG 8 handler=%#lx flags=%#x ONSTACK=%d  ", *(unsigned long*)$b, *(unsigned int*)($b+136), ((*(unsigned int*)($b+136)) & 0x08000000) != 0
info symbol *(unsigned long*)$b
call ((int(*)(int,void*,void*))__sigaction)(10, 0, (void*)$b)
printf "SIG 10 handler=%#lx flags=%#x ONSTACK=%d  ", *(unsigned long*)$b, *(unsigned int*)($b+136), ((*(unsigned int*)($b+136)) & 0x08000000) != 0
info symbol *(unsigned long*)$b
call ((int(*)(int,void*,void*))__sigaction)(11, 0, (void*)$b)
printf "SIG 11 handler=%#lx flags=%#x ONSTACK=%d  ", *(unsigned long*)$b, *(unsigned int*)($b+136), ((*(unsigned int*)($b+136)) & 0x08000000) != 0
info symbol *(unsigned long*)$b
call ((int(*)(int,void*,void*))__sigaction)(12, 0, (void*)$b)
printf "SIG 12 handler=%#lx flags=%#x ONSTACK=%d  ", *(unsigned long*)$b, *(unsigned int*)($b+136), ((*(unsigned int*)($b+136)) & 0x08000000) != 0
info symbol *(unsigned long*)$b
call ((int(*)(int,void*,void*))__sigaction)(13, 0, (void*)$b)
printf "SIG 13 handler=%#lx flags=%#x ONSTACK=%d  ", *(unsigned long*)$b, *(unsigned int*)($b+136), ((*(unsigned int*)($b+136)) & 0x08000000) != 0
info symbol *(unsigned long*)$b
call ((int(*)(int,void*,void*))__sigaction)(14, 0, (void*)$b)
printf "SIG 14 handler=%#lx flags=%#x ONSTACK=%d  ", *(unsigned long*)$b, *(unsigned int*)($b+136), ((*(unsigned int*)($b+136)) & 0x08000000) != 0
info symbol *(unsigned long*)$b
call ((int(*)(int,void*,void*))__sigaction)(17, 0, (void*)$b)
printf "SIG 17 handler=%#lx flags=%#x ONSTACK=%d  ", *(unsigned long*)$b, *(unsigned int*)($b+136), ((*(unsigned int*)($b+136)) & 0x08000000) != 0
info symbol *(unsigned long*)$b
call ((int(*)(int,void*,void*))__sigaction)(23, 0, (void*)$b)
printf "SIG 23 handler=%#lx flags=%#x ONSTACK=%d  ", *(unsigned long*)$b, *(unsigned int*)($b+136), ((*(unsigned int*)($b+136)) & 0x08000000) != 0
info symbol *(unsigned long*)$b
call ((int(*)(int,void*,void*))__sigaction)(27, 0, (void*)$b)
printf "SIG 27 handler=%#lx flags=%#x ONSTACK=%d  ", *(unsigned long*)$b, *(unsigned int*)($b+136), ((*(unsigned int*)($b+136)) & 0x08000000) != 0
info symbol *(unsigned long*)$b
call ((int(*)(int,void*,void*))__sigaction)(28, 0, (void*)$b)
printf "SIG 28 handler=%#lx flags=%#x ONSTACK=%d  ", *(unsigned long*)$b, *(unsigned int*)($b+136), ((*(unsigned int*)($b+136)) & 0x08000000) != 0
info symbol *(unsigned long*)$b
detach
quit
