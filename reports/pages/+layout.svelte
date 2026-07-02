<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import './wordleaves-theme.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	export let data;
</script>

<EvidenceDefaultLayout {data} title="Lucencies">
	<slot slot="content" />
</EvidenceDefaultLayout>
