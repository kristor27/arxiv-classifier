<script lang="ts">
	import { CATEGORY_NAMES } from '$lib/format';
	import { live } from '$lib/live.svelte';

	const s = $derived(live.stats);
	const cols = $derived([
		{ e: 'jev' as const, label: 'Jev' },
		{ e: 'llm' as const, label: s?.engines.llm ?? 'LLM' }
	]);
</script>

<figure class="card p-5">
	<figcaption class="caption"><b>Table 2.</b>Most frequent confusions: the true category, then what the model answered.</figcaption>
	<div class="mt-3 grid grid-cols-2 gap-4">
		{#each cols as c (c.e)}
			<div class="min-w-0">
				<p class="mb-1.5 flex items-center gap-1.5 text-xs font-medium"><span class="size-2 rounded-full" style="background: var(--{c.e})"></span>{c.label}</p>
				<ul class="grid gap-1 font-mono text-[11px]">
					{#each s?.confusions[c.e] ?? [] as m (m.truth + m.predicted)}
						<li class="flex items-center gap-1" title="{CATEGORY_NAMES[m.truth]} papers labelled {CATEGORY_NAMES[m.predicted]}">
							<span class="text-text-2">{m.truth}</span><span class="text-muted">→</span><span class="text-crit">{m.predicted}</span>
							<span class="num ml-auto font-sans text-muted">×{m.n}</span>
						</li>
					{:else}
						<li class="font-sans text-muted">none yet</li>
					{/each}
				</ul>
			</div>
		{/each}
	</div>
</figure>
