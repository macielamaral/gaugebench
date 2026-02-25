.PHONY: demo-offline demo-live demo-signed demo-wrap clean-demo \
        regen-unsigned-bundle regen-signed-bundle regen-wrap-bundle

# ---------------------------------------------------------------------------
# Demo targets
# ---------------------------------------------------------------------------

demo-offline:
	sh demo/demo_offline.sh

demo-live:
	sh demo/demo_live_mock.sh

demo-signed:
	sh demo/demo_live_signed.sh

demo-wrap:
	sh demo/demo_wrap.sh

# ---------------------------------------------------------------------------
# Bundle regeneration
# ---------------------------------------------------------------------------

regen-unsigned-bundle:
	rm -rf demo/bundles/demo_qic_aer
	GAUGEBENCH_DISABLE_SIGN=1 gaugebench run qic \
	    --backend aer \
	    --out demo/bundles/demo_qic_aer
	@echo "Bundle regenerated: demo/bundles/demo_qic_aer (unsigned)"

regen-signed-bundle:
	rm -rf demo/bundles/demo_qic_aer_signed
	gaugebench run qic \
	    --backend aer \
	    --out demo/bundles/demo_qic_aer_signed
	@echo "Bundle regenerated: demo/bundles/demo_qic_aer_signed (signed)"

regen-wrap-bundle:
	rm -rf demo/bundles/demo_wrapped_constellation_out
	gaugebench wrap \
	    --in  demo/bundles/demo_wrapped_constellation_in \
	    --out demo/bundles/demo_wrapped_constellation_out \
	    --engine constellation \
	    --backend quantum_elements
	@echo "Bundle regenerated: demo/bundles/demo_wrapped_constellation_out"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean-demo:
	rm -rf runs/tmp_* /tmp/gaugebench_demo_* /tmp/gaugebench_wrap_*
