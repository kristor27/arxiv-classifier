<script lang="ts">
	import { CATEGORY_NAMES, fmtTimes, ms, usd } from '$lib/format';
	import { live } from '$lib/live.svelte';
	import type { Judgement } from '$lib/types';

	// Invented abstracts (not real papers), each sitting between two categories on purpose.
	const PRESETS = [
		{ name: 'RAG agents', title: 'Retrieval Budgets for Tool-Using Language Agents',
			abstract: 'Language agents that call a search tool often retrieve far more documents than they read. We model retrieval as a budgeted decision and train a small policy that decides, at each step, whether another query is worth its cost. On three open-domain question answering benchmarks the policy cuts retrieval calls by 58% with no loss in exact-match accuracy, and transfers to unseen search engines without retraining.' },
		{ name: '5G intrusion', title: 'A Lightweight Intrusion Detector for 5G Edge Nodes',
			abstract: 'Edge nodes in 5G networks see traffic patterns that differ sharply from data-centre traffic, and existing intrusion detectors either miss slow attacks or overwhelm operators with false alarms. We present a streaming detector that fits in 40 MB of memory, learns per-cell baselines online, and flags signalling-storm and spoofing attacks within two seconds. In a six-week deployment on a regional operator it reduced false alarms by 71%.' },
		{ name: 'Robot doors', title: 'Opening Doors by Watching People',
			abstract: 'We teach a quadruped robot with an arm to open unfamiliar doors using only videos of people doing it. A hand-pose tracker extracts the motion of the handle from each video, and a reinforcement learning policy trained in simulation learns to reproduce it with the robot gripper. The robot opens 83% of 40 real doors it has never seen, including push bars and lever handles.' }
	];

	type Lane = { engine: 'jev' | 'llm'; label: string; elapsed: number; result: Judgement | null; error: string | null };
	let form = $state({ ...PRESETS[0] });
	let lanes = $state<Lane[]>([]);
	let running = $state(false);

	// Both requests leave at the same instant. The bars grow in real time, on the same scale.
	async function race() {
		running = true;
		lanes = [
			{ engine: 'jev', label: 'Jev', elapsed: 0, result: null, error: null },
			{ engine: 'llm', label: live.stats?.engines.llm ?? 'LLM', elapsed: 0, result: null, error: null }
		];
		const t0 = performance.now();
		let frame = requestAnimationFrame(function tick() {
			for (const l of lanes) if (!l.result && !l.error) l.elapsed = performance.now() - t0;
			frame = requestAnimationFrame(tick);
		});
		const body = JSON.stringify({ title: form.title, abstract: form.abstract });
		await Promise.all(
			lanes.map(async (lane) => {
				try {
					const r = await fetch(`/api/judge/${lane.engine}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body });
					const data = await r.json();
					lane.elapsed = performance.now() - t0;
					if (r.ok) lane.result = data;
					else lane.error = /402|credit/.test(String(data.detail)) ? 'Out of API credits' : String(data.detail?.[0]?.msg ?? data.detail ?? r.status).slice(0, 80);
				} catch {
					lane.error = 'Network error';
				}
			})
		);
		cancelAnimationFrame(frame);
		running = false;
	}

	const scale = $derived(Math.max(2000, ...lanes.map((l) => l.elapsed)));
	const [jev, llm] = $derived([lanes[0]?.result, lanes[1]?.result]);
	const top = (j: Judgement) => Object.entries(j.probabilities ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 3);
</script>

<section class="card p-5">
	<p class="caption"><b>Submit a paper.</b>Paste any title and abstract. Both models receive it at the same instant.</p>
	<div class="mt-3 flex flex-wrap gap-1.5">
		{#each PRESETS as p (p.name)}
			<button onclick={() => (form = { ...p })}
				class="rounded-full border px-2.5 py-1 text-xs transition {form.title === p.title ? 'border-text bg-text text-surface' : 'border-border text-text-2 hover:border-muted'}">{p.name}</button>
		{/each}
	</div>
	<div class="mt-3 grid gap-2 text-sm">
		<label class="grid gap-1"><span class="text-xs text-muted">Title</span>
			<input bind:value={form.title} maxlength="400" class="rounded-sm border border-border bg-surface-2 px-3 py-1.5 font-serif text-[0.95rem] outline-jev" /></label>
		<label class="grid gap-1"><span class="text-xs text-muted">Abstract</span>
			<textarea bind:value={form.abstract} maxlength="4000" rows="5" class="resize-y rounded-sm border border-border bg-surface-2 px-3 py-1.5 font-serif text-[0.85rem] leading-relaxed outline-jev"></textarea></label>
	</div>
	<button onclick={race} disabled={running}
		class="mt-3 w-full rounded-sm bg-text py-2 text-sm font-semibold text-surface transition hover:opacity-90 disabled:opacity-60">
		{running ? 'Racing…' : 'Race ⚡'}
	</button>

	{#if lanes.length}
		<div class="mt-4 grid gap-3">
			{#each lanes as lane (lane.engine)}
				<div>
					<div class="mb-1 flex items-center justify-between text-xs">
						<span class="inline-flex items-center gap-1.5 font-medium"><span class="size-2 rounded-full" style="background: var(--{lane.engine})"></span>{lane.label}</span>
						<span class="num font-mono {lane.result ? 'text-text' : 'text-muted'}">{ms(lane.elapsed)}</span>
					</div>
					<div class="h-2 overflow-hidden rounded-full bg-surface-2">
						<div class="h-full rounded-full {lane.error ? 'opacity-30' : ''}" style="width: {(lane.elapsed / scale) * 100}%; background: var(--{lane.engine})"></div>
					</div>
					<div class="mt-2 min-h-6 text-xs text-muted">
						{#if lane.result}
							<p><b class="font-mono text-text">{lane.result.category}</b> {CATEGORY_NAMES[lane.result.category] ?? ''} · {lane.result.paper_type}
								· <span class="num">{usd(lane.result.cost)}</span></p>
							<p class="num mt-0.5">
								{#if lane.result.probabilities}
									{#each top(lane.result) as [c, p], i (c)}{i ? ' · ' : ''}{c} {Math.round(p * 100)}%{/each}
								{:else}
									self-reported confidence {Math.round(lane.result.confidence * 100)}%
								{/if}
							</p>
						{:else if lane.error}
							<p class="text-warn">⚠ {lane.error}</p>
						{/if}
					</div>
				</div>
			{/each}
		</div>
		{#if jev && llm}
			<p class="mt-2 border-t border-border pt-3 font-serif text-[0.95rem]">
				Jev was <b class="num">{fmtTimes(llm.ms / jev.ms)}</b> faster and <b class="num">{fmtTimes(llm.cost / jev.cost)}</b> cheaper{jev.category === llm.category ? ', same answer.' : `, and they disagree.`}
			</p>
		{/if}
	{/if}
</section>
