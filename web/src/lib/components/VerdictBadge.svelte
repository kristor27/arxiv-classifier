<script lang="ts">
	import { VERDICTS } from '$lib/format';
	import type { Verdict } from '$lib/types';

	let { verdict, size = 'md' }: { verdict: Verdict; size?: 'sm' | 'md' } = $props();
	const v = $derived(VERDICTS[verdict]);
</script>

<span
	class="inline-flex items-center gap-1.5 rounded-full font-medium whitespace-nowrap {size === 'sm'
		? 'px-2 py-0.5 text-[11px]'
		: 'px-2.5 py-1 text-xs'}"
	style="color: {v.color}; background: color-mix(in oklab, {v.color} 14%, transparent)"
>
	<span
		class="grid place-items-center rounded-full text-[9px] font-bold text-white {size === 'sm' ? 'size-3.5' : 'size-4'}"
		style="background: {v.color}"
		aria-hidden="true">{v.icon}</span
	>
	{v.label}
</span>
